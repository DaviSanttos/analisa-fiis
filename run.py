import os
import sys
import subprocess
import time
import webbrowser
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


def main():
    print("=" * 60)
    print("  ANALISA FIIs - Sistema de Monitoramento Inteligente")
    print("=" * 60)

    api_port = int(os.getenv("PORT", "8000"))
    streamlit_port = int(os.getenv("STREAMLIT_PORT", "8501"))

    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app",
         "--host", "0.0.0.0", "--port", str(api_port)],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    print(f"\n✅ API rodando em: http://localhost:{api_port}")
    print(f"📖 Documentação: http://localhost:{api_port}/docs")

    time.sleep(2)

    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run",
         "frontend/dashboard.py",
         "--server.port", str(streamlit_port),
         "--server.headless", "true"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    dashboard_url = f"http://localhost:{streamlit_port}"
    print(f"📊 Dashboard: {dashboard_url}")
    print(f"\nPressione Ctrl+C para parar tudo.\n")

    webbrowser.open(dashboard_url)

    try:
        api_proc.wait()
    except KeyboardInterrupt:
        print("\nParando serviços...")
        api_proc.terminate()
        streamlit_proc.terminate()
        print("Serviços parados.")


if __name__ == "__main__":
    main()
