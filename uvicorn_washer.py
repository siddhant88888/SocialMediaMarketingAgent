import os
import sys
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Add the parent directory to sys.path to import the API modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smma_apis.linkedIn import LinkedinAutomate
from smma_apis import x_api2
from smma_apis import insta_api 
from smma_apis import facebook_api 
from smma_apis import upload_to_drive

load_dotenv()

app = FastAPI(
    title="Social Media Posting API",
    description="API for posting content to various social media platforms",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class PostRequest(BaseModel):
    content: str
    media_type: str

# @app.post("/generate_content")
# async def gen_cont():

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = upload_to_drive.upload_photo(file.file)
    media_url = upload_to_drive.get_download_link(file_id)
    return {"media_url": media_url}

@app.post("/post/linkedin")
async def post_to_linkedin(request: PostRequest, media_url: str = Form(None)):
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    title = request.content[:50]  # Using first 50 characters as title
    try:
        LinkedinAutomate(access_token, media_url, title, request.content, request.media_type).main_func()
        return {"message": "Posted successfully to LinkedIn"}
    except Exception as e:
        return {"error": f"Failed to post to LinkedIn: {str(e)}"}

@app.post("/post/twitter")
async def post_to_twitter(request: PostRequest, media_url: str = Form(None)):
    try:
        x_api2.post_tweet_with_image(request.content, media_url)
        return {"message": "Posted successfully to Twitter"}
    except Exception as e:
        return {"error": f"Failed to post to Twitter: {str(e)}"}

@app.post("/post/instagram")
async def post_to_instagram(request: PostRequest, media_url: str = Form(None)):
    try:
        insta_api.post_to_instagram(request.content, media_url, request.media_type)
        return {"message": "Posted successfully to Instagram"}
    except Exception as e:
        return {"error": f"Failed to post to Instagram: {str(e)}"}

@app.post("/post/facebook")
async def post_to_facebook(request: PostRequest, media_url: str = Form(None)):
    user_access_token = os.environ.get("FACEBOOK_USER_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    
    if not user_access_token or not page_id:
        return {"error": "Facebook user access token or page ID not found in environment variables."}

    page_access_token = facebook_api.get_page_access_token(page_id, user_access_token)
    
    if page_access_token:
        try:
            facebook_api.post_fb(page_id, page_access_token, request.content, media_url, request.media_type)
            return {"message": "Posted successfully to Facebook"}
        except Exception as e:
            return {"error": f"Failed to post to Facebook: {str(e)}"}
    else:
        return {"error": "Failed to obtain Page Access Token."}

@app.post("/post/all")
async def post_to_all(request: PostRequest, media_url: str = Form(None)):
    results = {}
    
    # Upload to Google Drive and get the download link
    file_id = upload_to_drive.upload_photo(media_url)
    media_url_for_graph = upload_to_drive.get_download_link(file_id)

    # Post to Facebook
    try:
        await post_to_facebook(request, media_url_for_graph)
        results["facebook"] = "Success"
    except Exception as e:
        results["facebook"] = f"Error: {str(e)}"

    # Post to Instagram
    try:
        await post_to_instagram(request, media_url_for_graph)
        results["instagram"] = "Success"
    except Exception as e:
        results["instagram"] = f"Error: {str(e)}"

    # Post to Twitter
    try:
        await post_to_twitter(request, media_url)
        results["twitter"] = "Success"
    except Exception as e:
        results["twitter"] = f"Error: {str(e)}"

    # Post to LinkedIn
    try:
        await post_to_linkedin(request, media_url)
        results["linkedin"] = "Success"
    except Exception as e:
        results["linkedin"] = f"Error: {str(e)}"

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "uvicorn_washer:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[".", "smma_apis"],
        reload_includes=["*.py"],
    )
