"""自签名证书生成与 HTTPS/HTTP 启动入口。从旧版单文件播放器移植。"""

import argparse
import atexit
import datetime
import ipaddress
import socket
import sys
import tempfile
from pathlib import Path

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .config import BACKEND_DIR

DEFAULT_PORTS = [2053, 2087, 8443]


def _fix_console_encoding() -> None:
    """Windows 控制台默认 GBK，强制 UTF-8 输出避免中文/emoji 打印崩溃。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def generate_self_signed_cert(cert_file: str | None = None, key_file: str | None = None):
    """生成 localhost 自签名证书；无文件路径时用临时目录（退出自动清理）。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Music"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3650)
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    if cert_file and key_file:
        with open(cert_file, "wb") as f:
            f.write(cert_pem)
        with open(key_file, "wb") as f:
            f.write(key_pem)
        return cert_pem, key_pem, cert_file, key_file

    temp_dir = Path(tempfile.mkdtemp(prefix="music_cert_"))
    cert_path = temp_dir / "cert.pem"
    key_path = temp_dir / "key.pem"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    def cleanup():
        for p in (cert_path, key_path):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass

    atexit.register(cleanup)
    return cert_pem, key_pem, str(cert_path), str(key_path)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


def main() -> None:
    _fix_console_encoding()

    parser = argparse.ArgumentParser(description="Music Server")
    parser.add_argument("--save-cert", action="store_true", help="保存证书到 backend/ 目录")
    parser.add_argument("--cert-dir", type=str, default=None, help="指定证书保存目录")
    parser.add_argument("--port", type=int, default=None, help="指定端口号")
    args = parser.parse_args()

    save_cert = args.save_cert or args.cert_dir is not None

    if args.port:
        ports_to_try = [args.port]
    else:
        ports_to_try = list(DEFAULT_PORTS)
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.bind(("0.0.0.0", 443))
            test_sock.close()
            ports_to_try.insert(0, 443)
        except OSError:
            pass

    if save_cert:
        if args.cert_dir:
            cert_dir = Path(args.cert_dir)
        else:
            cert_dir = BACKEND_DIR
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert_file = str(cert_dir / "music_cert.pem")
        key_file = str(cert_dir / "music_key.pem")
        print(f"证书将保存到: {cert_file}")
    else:
        cert_file = key_file = None

    print("正在生成自签名证书...")
    try:
        _, _, cert_path, key_path = generate_self_signed_cert(cert_file, key_file)
        print("证书生成成功" + ("（临时文件，退出时自动删除）" if not save_cert else ""))
    except Exception as e:
        print(f"证书生成失败: {e}，回退 HTTP 模式")
        port = _free_port()
        print(f"访问地址: http://127.0.0.1:{port}")
        uvicorn.run("app:app", host="0.0.0.0", port=port)
        return

    for port in ports_to_try:
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(("0.0.0.0", port))
            test_sock.close()
        except OSError as e:
            print(f"端口 {port} 不可用: {e}")
            continue

        print(f"访问地址: https://127.0.0.1:{port}")
        print('注意: 浏览器会提示证书不受信任，点击"高级"→"继续访问"即可')
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=port,
            ssl_certfile=cert_path,
            ssl_keyfile=key_path,
        )
        return

    print("所有 HTTPS 端口都不可用，使用 HTTP 模式")
    port = _free_port()
    print(f"访问地址: http://127.0.0.1:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
