#!/usr/bin/env python3
"""
LINE Bot起動スクリプト
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import uvicorn
from agri_ai.line_bot.app import app


def main():
    """メイン関数"""
    print("🚀 農業AI LINE Bot 起動中...")
    print("=" * 60)
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check environment variables
        required_vars = [
            'MONGODB_URI',
            'GOOGLE_API_KEY',
            'LINE_CHANNEL_ACCESS_TOKEN',
            'LINE_CHANNEL_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
                missing_vars.append(var)
        
        if missing_vars:
            print("❌ 必要な環境変数が設定されていません:")
            for var in missing_vars:
                print(f"  - {var}")
            print("\n.envファイルを確認してください。")
            sys.exit(1)
        
        # Start server
        print("✅ 環境変数の確認完了")
        print("🌐 サーバーを起動中...")
        print("📱 LINE Bot Webhook URL: http://localhost:8000/webhook")
        print("🔧 管理画面: http://localhost:8000/docs")
        print("❤️  ヘルスチェック: http://localhost:8000/health")
        print("=" * 60)
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止中...")
        print("✅ 農業AI LINE Bot 停止完了")
    
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()