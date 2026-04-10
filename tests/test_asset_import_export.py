import pytest
import openpyxl
import io
from services.asset_service import AssetService


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def asset_service(db_session):
    return AssetService(db_session)


def test_export_assets(asset_service):
    asset_service.create(
        unit_name="Unit1",
        system_name="System1",
        username="admin",
        password="pass123",
        ip="192.168.1.1",
        port=22
    )
    asset_service.create(
        unit_name="Unit2",
        system_name="System2",
        username="root",
        password="pass456",
        ip="192.168.1.2",
        port=22
    )

    file_data = asset_service.export_assets(include_password=False)
    assert file_data is not None
    assert len(file_data) > 0

    workbook = openpyxl.load_workbook(io.BytesIO(file_data))
    worksheet = workbook.active
    
    assert worksheet.max_row == 3
    
    headers = [cell.value for cell in worksheet[1]]
    expected_headers = [
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名",
        "端口", "主机名", "业务服务", "位置", "服务器类型", "VIP", "备注"
    ]
    assert headers == expected_headers
    assert "密码" not in headers


def test_export_assets_with_password(asset_service):
    asset_service.create(
        unit_name="Unit1",
        system_name="System1",
        username="admin",
        password="secret123",
        ip="192.168.1.1",
        port=22
    )

    file_data = asset_service.export_assets(include_password=True)
    assert file_data is not None

    workbook = openpyxl.load_workbook(io.BytesIO(file_data))
    worksheet = workbook.active
    
    headers = [cell.value for cell in worksheet[1]]
    expected_headers = [
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名",
        "密码", "端口", "主机名", "业务服务", "位置", "服务器类型", "VIP", "备注"
    ]
    assert headers == expected_headers
    assert "密码" in headers
    
    password_col = headers.index("密码") + 1
    assert worksheet.cell(row=2, column=password_col).value == "secret123"


def test_export_selected_assets(asset_service):
    asset_id1 = asset_service.create("Unit1", "System1", "admin", "pass", ip="192.168.1.1", port=22)
    asset_id2 = asset_service.create("Unit2", "System2", "admin", "pass", ip="192.168.1.2", port=22)
    asset_service.create("Unit3", "System3", "admin", "pass", ip="192.168.1.3", port=22)

    file_data = asset_service.export_assets(asset_ids=[asset_id1, asset_id2])
    workbook = openpyxl.load_workbook(io.BytesIO(file_data))
    worksheet = workbook.active
    
    assert worksheet.max_row == 3


def test_import_assets_excel(asset_service):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码", "端口"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.1", "", "admin", "pass123", 22])
    worksheet.append(["Unit2", "System2", "192.168.1.2", "", "root", "pass456", 22])
    
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue()
    )

    assert success_count == 2
    assert fail_count == 0
    assert len(errors) == 0

    assets = asset_service.get_all()
    assert len(assets) == 2


def test_import_assets_missing_required_fields(asset_service):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "用户名"
    ])
    worksheet.append(["Unit1", "", "admin"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue(),
        skip_errors=True
    )

    assert success_count == 0
    assert fail_count == 1
    assert len(errors) > 0
    assert "缺少必填字段" in errors[0]


def test_import_assets_update_existing(asset_service):
    asset_service.create("Unit1", "System1", "admin", "oldpass", ip="192.168.1.1", port=22)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码", "端口"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.1", "", "admin", "newpass", 2222])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue(),
        update_existing=True
    )

    assert success_count == 1
    assert fail_count == 0

    assets = asset_service.get_all()
    assert len(assets) == 1
    assert assets[0].username == "admin"
    assert assets[0].ip == "192.168.1.1"
    assert assets[0].port == 2222
    assert asset_service.get_password(assets[0].id) == "newpass"


def test_import_assets_duplicate_without_update(asset_service):
    asset_service.create("Unit1", "System1", "admin", "pass", ip="192.168.1.1", port=22)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.1", "", "admin", "pass"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue(),
        update_existing=False,
        skip_errors=True
    )

    assert success_count == 0
    assert fail_count == 1
    assert "资产已存在" in errors[0]


def test_import_assets_missing_ip_and_ipv6(asset_service):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "", "", "admin", "pass"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue(),
        skip_errors=True
    )

    assert success_count == 0
    assert fail_count == 1
    assert "IP地址和IPv6地址至少需要填写一个" in errors[0]


def test_import_assets_same_unit_system_different_ip(asset_service):
    asset_service.create("Unit1", "System1", "admin", "pass", ip="192.168.1.1", port=22)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.2", "", "admin", "pass"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue()
    )

    assert success_count == 1
    assert fail_count == 0

    assets = asset_service.get_all()
    assert len(assets) == 2


def test_import_assets_same_unit_system_ip_different_user(asset_service):
    asset_service.create("Unit1", "System1", "admin", "pass", ip="192.168.1.1", port=22)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.1", "", "root", "pass"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue()
    )

    assert success_count == 1
    assert fail_count == 0

    assets = asset_service.get_all()
    assert len(assets) == 2


def test_import_assets_with_ipv6_only(asset_service):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "", "2001:db8::1", "admin", "pass"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue()
    )

    assert success_count == 1
    assert fail_count == 0

    assets = asset_service.get_all()
    assert len(assets) == 1
    assert assets[0].ipv6 == "2001:db8::1"


def test_import_assets_skip_errors(asset_service):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append([
        "单位名称", "系统名称", "IP地址", "IPv6地址", "用户名", "密码"
    ])
    worksheet.append(["Unit1", "System1", "192.168.1.1", "", "admin", "pass1"])
    worksheet.append(["", "System2", "192.168.1.2", "", "admin", "pass2"])
    worksheet.append(["Unit2", "System2", "192.168.1.3", "", "root", "pass3"])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=output.getvalue(),
        skip_errors=True
    )

    assert success_count == 2
    assert fail_count == 1
    assert len(errors) == 1


def test_import_export_roundtrip(asset_service):
    asset_service.create("Unit1", "System1", "admin", "pass123", "192.168.1.1", 22)
    asset_service.create("Unit2", "System2", "root", "pass456", "192.168.1.2", 2222)

    file_data = asset_service.export_assets(include_password=True)

    from models.server_asset import ServerAsset
    asset_service.db.query(ServerAsset).delete()
    asset_service.db.commit()

    success_count, fail_count, errors = asset_service.import_assets(
        file_data=file_data
    )

    assert success_count == 2
    assert fail_count == 0

    assets = asset_service.get_all()
    assert len(assets) == 2
    assert assets[0].unit_name == "Unit1"
    assert assets[1].unit_name == "Unit2"
