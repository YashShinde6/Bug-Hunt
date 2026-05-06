import asyncio
import base64
import httpx
from config import settings

async def main():
    from PIL import Image
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new('RGB', (100, 100), color = (73, 109, 137))
        img.save(f.name)
        img_path = f.name
        
    with open(img_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{
                        "parts": [
                            {"text": "What is in this image?"},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": base64_image,
                                }
                            }
                        ]
                    }],
                }
            )
            print(response.status_code)
            print(response.json())
    except Exception as e:
        print(e)
    
if __name__ == "__main__":
    asyncio.run(main())
