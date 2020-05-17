import webvtt
import json
import sys
from io import StringIO
from urllib.parse import urlparse
from multiprocessing.pool import ThreadPool
from utils import get_session, get_w3_info


def scrape_youtube(url):
    transcript_log = []
    with get_session() as ses:
        res = ses.get(url)
        title = res.text.split('og:title" content="')[1].split('">')[0].strip()
        innertube_api_key = res.text.split('"INNERTUBE_API_KEY":"')[
            1].split('"')[0]
        client_screen_nonce = res.text.split('"EVENT_ID":"')[1].split('"')[0]
        click_tracking_params = res.text.split('engagement-panel-transcript')[
            1].split('"clickTrackingParams":"')[1].split('"')[0]
        params = res.text.split('serializedShareEntity":"')[1].split('"')[0]
        ytcfg = json.loads(res.text.split(
            '"INNERTUBE_CONTEXT":')[1].split('});')[0])

        payload = {
            "context": {
                **ytcfg,
                "user": {},
                "clientScreenNonce": client_screen_nonce,
                "clickTracking": {
                    "clickTrackingParams": click_tracking_params
                }
            },
            "params": params
        }

        res = ses.post(
            'https://www.youtube.com/youtubei/v1/get_transcript?key=' + innertube_api_key, json=payload)

        transcript = res.json()

        for action in transcript['actions']:
            for group in action['updateEngagementPanelAction']['content']['transcriptRenderer']['body']['transcriptBodyRenderer']['cueGroups']:
                for cue in group['transcriptCueGroupRenderer']['cues']:
                    time = group['transcriptCueGroupRenderer']['formattedStartOffset']['simpleText']
                    text = cue['transcriptCueRenderer']['cue']['simpleText']
                    transcript_log.append((time, text))

        return (title, transcript_log)


def scrape_3c_media(url):
    transcript_log = []
    with get_session() as ses:
        title, config = get_w3_info(ses.get(url))
        for video in config['playlist']:
            for track in video['tracks']:
                with StringIO(ses.get(track['file']).text) as captions:
                    for caption in webvtt.read_buffer(captions):
                        transcript_log.append((caption.start, caption.text))
    return (title, transcript_log)


netloc_map = {
    'www.3cmediasolutions.org': scrape_3c_media,
    'www.youtube.com': scrape_youtube,
    'youtu.be': scrape_youtube
}


def handle_raw_url(url):
    url_components = urlparse(url)
    return (url, *netloc_map[url_components.netloc](url))


def scrape_transcripts_from_urls(urls, processes=10):
    if processes > 1:
        with ThreadPool(processes=processes) as pool:
            return pool.map(handle_raw_url, urls)
    else:
        return [handle_raw_url(url) for url in urls]


def m_s_to_s(minutes: str, seconds: str) -> str:
    return str(int(seconds) + (int(minutes) * 60))


def prep_markdown(url):
    url, title, transcript = handle_raw_url(url)
    url_components = urlparse(url)
    header = f'# [{title}]({url})\n\n'
    body = ''
    for time, text in transcript:
        if url_components.netloc != 'www.3cmediasolutions.org':
            if url_components.query:
                time_url = url + '&t=' + m_s_to_s(*time.split(':'))
            else:
                time_url = url + '?t=' + m_s_to_s(*time.split(':'))
            body += f'\n\n[`{time}`]({time_url}) : {text}'
        else:
            body += f'\n\n`{time}` : {text}'
    return (header, body)


def add_pdf_to_preped_md(pdf_path, header, body):
    md = header
    md += f'\n<iframe src="{pdf_path}" width="100%" height="500px"></iframe>\n'
    md += body
    return md


if __name__ == '__main__':
    for url, title, transcript in scrape_transcripts_from_urls(sys.argv[1:]):
        url_components = urlparse(url)
        print(f'# [{title}]({url})')
        for time, text in transcript:
            if url_components.netloc == 'www.youtube.com':
                if url_components.query:
                    time_url = url + '&t=' + m_s_to_s(*time.split(':'))
                else:
                    time_url = url + '?t=' + m_s_to_s(*time.split(':'))
                print(f'\n[`{time}`]({time_url}) : {text}')
            else:
                print(f'\n`{time}` : {text}')
        print('\n\n')
