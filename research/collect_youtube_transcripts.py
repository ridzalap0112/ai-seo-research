"""
Collect YouTube transcripts and save them as Markdown files.

Installation:
    pip install youtube-transcript-api

Usage:
    1. Edit the VIDEOS list below with expert names and YouTube URLs.
    2. Run:
        python collect_youtube_transcripts.py

Output:
    Transcripts are saved inside:
        research/youtube-transcripts/

File naming format:
    expert-name-video-title.md

Notes:
    - This script does not download audio or video.
    - Some videos do not have transcripts, have disabled transcripts, or only
      provide transcripts in languages not requested below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


OUTPUT_DIR = Path("research") / "youtube-transcripts"
PREFERRED_LANGUAGES = ("en", "en-US", "en-GB")


@dataclass(frozen=True)
class VideoTarget:
    expert_name: str
    url: str
    title: str = ""
    channel: str = ""


VIDEOS: list[VideoTarget] = [
    VideoTarget(
        expert_name="Mike King",
        url="https://www.youtube.com/watch?v=p0XPAM-kQUk",
        title="SEO Is Not Ready for What AI Is About to Do",
        channel="iPullRank"
    ),

    VideoTarget(
        expert_name="Mike King",
        url="https://www.youtube.com/watch?v=xKuZzur3yoA",
        title="Relevance Engineering: How CMOs Should Approach AI Search",
        channel="iPullRank"
    ),

    VideoTarget(
        expert_name="Mike King",
        url="https://www.youtube.com/watch?v=2HApQVWyMkE",
        title="Why Cutting Content Is the Wrong Move for AI Search Visibility",
        channel="iPullRank"
    ),
]


def extract_video_id(url: str) -> str:
    """Extract a YouTube video ID from common YouTube URL formats."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            video_id = parsed.path.strip("/").split("/")[1]
        else:
            video_id = ""
    else:
        video_id = ""

    if not re.fullmatch(r"[\w-]{11}", video_id):
        raise ValueError(f"Could not extract a valid YouTube video ID from: {url}")

    return video_id


def slugify(value: str) -> str:
    """Convert text into a safe lowercase filename slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "untitled"


def get_transcript(video_id: str) -> str:
    """Fetch a transcript and return it as readable plain text."""
    api = YouTubeTranscriptApi()
    transcript = api.fetch(
        video_id,
        languages=list(PREFERRED_LANGUAGES),
    )
    return "\n".join(snippet.text.strip() for snippet in transcript if snippet.text)


def build_markdown(
    *,
    video_title: str,
    channel: str,
    url: str,
    transcript: str,
) -> str:
    collected_on = date.today().isoformat()
    return (
        f"# {video_title}\n\n"
        f"# Channel\n\n"
        f"{channel or 'Unknown'}\n\n"
        f"# URL\n\n"
        f"{url}\n\n"
        f"# Date Collected\n\n"
        f"{collected_on}\n\n"
        f"# Transcript\n\n"
        f"{transcript}\n"
    )


def save_transcript(video: VideoTarget) -> Path:
    video_id = extract_video_id(video.url)
    transcript = get_transcript(video_id)

    video_title = video.title or video_id
    filename = f"{slugify(video.expert_name)}-{slugify(video_title)}.md"
    output_path = OUTPUT_DIR / filename

    markdown = build_markdown(
        video_title=video_title,
        channel=video.channel,
        url=video.url,
        transcript=transcript,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def main() -> None:
    if not VIDEOS:
        print("No videos configured. Add VideoTarget entries to the VIDEOS list.")
        return

    for video in VIDEOS:
        try:
            output_path = save_transcript(video)
        except ValueError as error:
            print(f"[invalid-url] {video.url}: {error}")
        except TranscriptsDisabled:
            print(f"[disabled] Transcripts are disabled for: {video.url}")
        except NoTranscriptFound:
            print(f"[missing] No preferred-language transcript found for: {video.url}")
        except VideoUnavailable:
            print(f"[unavailable] Video is unavailable: {video.url}")
        except CouldNotRetrieveTranscript as error:
            print(f"[retrieve-error] Could not retrieve transcript for {video.url}: {error}")
        except OSError as error:
            print(f"[file-error] Could not write transcript for {video.url}: {error}")
        else:
            print(f"[saved] {output_path}")


if __name__ == "__main__":
    main()
