# scripts klasöründe yeni dosya: health_check.py
# İçeriği yapıştır:

# scripts/health_check.py
# ====================
"""
Weekly health check and usage monitoring
"""
from pathlib import Path
from datetime import datetime, timedelta
from utils.config import config
from utils.logger import logger
import json


def get_api_usage_estimate() -> dict:
    """
    Estimate API usage (since free APIs don't provide usage endpoints)
    Based on GitHub Actions run logs and local tracking
    """
    # This is a placeholder - extend with actual tracking
    return {
        "openrouter_requests": 0,  # Would track via local counter file
        "hf_zerogpu_seconds": 0,
        "leonardo_tokens": 0,
        "last_reset": datetime.now().date().isoformat()
    }


def check_storage_usage() -> dict:
    """Check GitHub artifact and local storage usage"""
    output_dir = config.OUTPUT_DIR
    total_size = sum(f.stat().st_size for f in output_dir.glob("*") if f.is_file())
    
    return {
        "output_files": len(list(output_dir.glob("*"))),
        "total_size_bytes": total_size,
        "total_size_mb": total_size / (1024 * 1024),
        "github_artifact_limit_gb": 5,
        "telegram_limit_mb": 50
    }


def generate_health_report() -> dict:
    """Generate comprehensive health report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "status": "healthy",
        "checks": {
            "config": config.is_ready(),
            "output_dir_exists": config.OUTPUT_DIR.exists(),
            "required_tools": {
                "ffmpeg": True,  # Would check via subprocess
                "piper": True,   # Would check model presence
            }
        },
        "usage": get_api_usage_estimate(),
        "storage": check_storage_usage(),
        "alerts": []
    }
    
    # Generate alerts
    if not report["checks"]["config"]:
        report["alerts"].append("⚠️ Configuration incomplete - check secrets")
        report["status"] = "warning"
    
    if report["storage"]["total_size_mb"] > 100:
        report["alerts"].append(f"⚠️ Output folder large: {report['storage']['total_size_mb']:.1f} MB")
    
    return report


def send_health_report_to_telegram(report: dict) -> bool:
    """Send health report to Telegram"""
    from scripts.send_telegram import send_to_telegram
    
    # Format report as text
    text = f"""📊 AI-KidsTube Health Report
🕐 {report['timestamp'][:10]}
🔖 v{report['version']}
🟢 Status: {report['status'].upper()}

✅ Checks:
• Config: {'OK' if report['checks']['config'] else 'MISSING'}
• Output dir: {'OK' if report['checks']['output_dir_exists'] else 'MISSING'}

💾 Storage: {report['storage']['total_size_mb']:.1f} MB

"""
    
    if report["alerts"]:
        text += "⚠️ Alerts:\n" + "\n".join(f"• {a}" for a in report["alerts"]) + "\n"
    
    # Create temp file for report
    report_path = config.OUTPUT_DIR / f"health_{datetime.now().strftime('%Y%m%d')}.txt"
    report_path.write_text(text, encoding="utf-8")
    
    # Send via Telegram
    return send_to_telegram(report_path, caption="📊 Haftalık Sistem Raporu")


if __name__ == "__main__":
    import sys
    
    report = generate_health_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    if "--send" in sys.argv:
        success = send_health_report_to_telegram(report)
        print(f"📤 Telegram: {'✅ Sent' if success else '❌ Failed'}")
# ====================
# Dosyayı kaydet ✅