import sys
import asyncio
import uvicorn


def secici_dongu_olustur():
    if sys.platform == "win32":
        dongu = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(dongu)
        return dongu
    return asyncio.new_event_loop()


create_selector_loop = secici_dongu_olustur

if __name__ == "__main__":
    dongu = secici_dongu_olustur()

    yapilandirma = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info",
        loop="none",
    )

    sunucu = uvicorn.Server(yapilandirma)
    print("[+] Pusula sunucusu başlatılıyor (http://0.0.0.0:5000)...")
    dongu.run_until_complete(sunucu.serve())
