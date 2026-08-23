import os
import time
from datetime import date
from pathlib import Path

import requests
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
CANVA_API_BASE = "https://api.canva.com/rest/v1"


def get_canva_token(client_id: str, client_secret: str) -> str:
    """Canva OAuth2.0でアクセストークンを取得する。"""
    resp = requests.post(
        f"{CANVA_API_BASE}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def create_design(token: str, template_id: str, title: str, summary: str) -> str:
    """テンプレートからデザインを作成してdesign_idを返す。"""
    if not template_id:
        raise ValueError("config.ymlのcanva.cover_template_idまたはsocial_template_idが未設定です")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{CANVA_API_BASE}/designs",
        json={"design_type": {"type": "custom"}, "asset_id": template_id},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    design_id = resp.json()["design"]["id"]

    requests.post(
        f"{CANVA_API_BASE}/designs/{design_id}/autofill",
        json={"data": {
            "title": {"type": "text", "text": title},
            "summary": {"type": "text", "text": summary[:50]},
        }},
        headers=headers,
        timeout=15,
    )
    return design_id


def export_design(token: str, design_id: str, timeout_sec: int = 60) -> str:
    """デザインをPNGとしてエクスポートしてURLを返す。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{CANVA_API_BASE}/exports",
        json={"design_id": design_id, "format": "png", "export_quality": "pro"},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    job_id = resp.json()["job"]["id"]

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        time.sleep(3)
        status_resp = requests.get(
            f"{CANVA_API_BASE}/exports/{job_id}", headers=headers, timeout=15
        )
        status_resp.raise_for_status()
        job = status_resp.json()["job"]
        if job["status"] == "success":
            return job["urls"][0]
        if job["status"] == "failed":
            raise RuntimeError(f"Canvaエクスポート失敗: {job}")

    raise TimeoutError(f"Canvaエクスポートが{timeout_sec}秒でタイムアウトしました")


def download_image(url: str, output_path: Path) -> None:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)


def generate_images(
    title: str,
    summary: str,
    client_id: str,
    client_secret: str,
    covers_dir: Path,
    social_dir: Path,
    count: int = 10,
) -> None:
    """表紙・告知画像をそれぞれcount枚生成して保存する。"""
    cover_template_id = CONFIG["canva"]["cover_template_id"]
    social_template_id = CONFIG["canva"]["social_template_id"]

    if not cover_template_id or not social_template_id:
        raise ValueError(
            "config.ymlのcanva.cover_template_idとsocial_template_idを設定してください。\n"
            "Canva Connect API: https://developers.canva.com"
        )

    token = get_canva_token(client_id, client_secret)
    today = date.today().isoformat()
    covers_dir.mkdir(parents=True, exist_ok=True)
    social_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, count + 1):
        cover_id = create_design(token, cover_template_id, title, summary)
        cover_url = export_design(token, cover_id)
        download_image(cover_url, covers_dir / f"{today}-cover-{i:02d}.png")
        print(f"  表紙 {i}/{count} 完了")

        social_id = create_design(token, social_template_id, title, summary)
        social_url = export_design(token, social_id)
        download_image(social_url, social_dir / f"{today}-social-{i:02d}.png")
        print(f"  告知画像 {i}/{count} 完了")


def main():
    client_id = os.environ["CANVA_CLIENT_ID"]
    client_secret = os.environ["CANVA_CLIENT_SECRET"]

    final_files = sorted(Path("articles/final").glob("*-final.md"))
    if not final_files:
        raise FileNotFoundError("articles/final/ にfinal.mdが見つかりません")

    content = final_files[-1].read_text(encoding="utf-8")
    lines = [l for l in content.split("\n") if l.strip()]
    title = lines[0].lstrip("# ").strip() if lines else "タイトル未設定"
    summary = " ".join(lines[1:5])[:200]

    generate_images(
        title=title,
        summary=summary,
        client_id=client_id,
        client_secret=client_secret,
        covers_dir=Path("assets/covers"),
        social_dir=Path("assets/social"),
    )
    print("✅ 画像生成完了")


if __name__ == "__main__":
    main()
