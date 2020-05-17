from tempfile import NamedTemporaryFile
import logging
import sys
import os
import multiprocessing
import subprocess
from uuid import uuid4
from tempfile import TemporaryDirectory, NamedTemporaryFile
import grip
from os import path
from glob import glob
from utils import get_session, get_w3_info, ThreadWithReturnValue
from io import BytesIO
from ocr import concat_images_as_pdf
from transcript import prep_markdown, add_pdf_to_preped_md
from cv import strip_slides
import cv2
from urllib.parse import urlparse


temp_dir = TemporaryDirectory()

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger('note-maker')


def download_youtube(url):
    location = path.join(temp_dir.name, str(uuid4()))
    process = subprocess.run(
        ['youtube-dl', '--output', location, url], capture_output=True)
    if b'ERROR' in process.stderr:
        log.error('youtube-dl encountered an error: %s',
                  process.stderr.decode())
        return None
    return glob(f'{location}*')[0]


def download_3c_media(url):
    with get_session() as ses:
        _, config = get_w3_info(ses.get(url))
        for video in config['playlist']:
            extension = video['file'].split('?')[0].split('.')[-1]
            location = path.join(temp_dir.name, str(uuid4()) + '.' + extension)
            with ses.get(video['file'], stream=True) as r, open(location, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            break
    return location


netloc_map = {
    'www.3cmediasolutions.org': download_3c_media,
    'www.youtube.com': download_youtube,
    'youtu.be': download_youtube
}


def worker(url):
    url_components = urlparse(url)
    log.info('beginnning download %s', url)
    location = netloc_map[url_components.netloc](url)
    log.info('download finished %s', location)
    if location:
        log.info('prepping markdown')
        thread = ThreadWithReturnValue(target=prep_markdown, args=(url,))
        thread.start()
        log.info('stripping slides')
        sildes = [BytesIO(cv2.imencode(".png", slid)[1])
                  for slid in strip_slides(location)]
        log.info('creating pdf')
        pdf_bytes_io = concat_images_as_pdf(sildes)

        log.info('saving pdf')
        os.makedirs('.pdfs', exist_ok=True)
        pdf_path = path.join('.pdfs', str(uuid4()) + '.pdf')

        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes_io.getvalue())

        preped_markdown = thread.join()

        log.info('inserting iframe')

        md = add_pdf_to_preped_md(pdf_path, *preped_markdown)

        return (url, md)
    return (url, None)


def markdown_to_html(markdown, html_file, title):
    markdown = markdown.replace('<', ':lt:').replace('>', ':gt:')

    with NamedTemporaryFile(mode='w') as md, NamedTemporaryFile(mode='r') as html, open(html_file, 'w') as f:
        md.write(markdown)
        md.flush()
        grip.export(
            title=title,
            path=md.name,
            out_filename=html.name,
            render_wide=True,
            quiet=True
        )
        for l in html:
            f.write(l.replace(':lt:', '<').replace(':gt:', '>'))


if __name__ == '__main__':
    multiprocessing.set_start_method('forkserver')

    log.info('created tmp directory %s', temp_dir.name)

    # data = [worker(u) for u in sys.argv[1:-1]]

    with multiprocessing.Pool(processes=10) as pool:
        data = pool.map(worker, sys.argv[1:-1])

    failed = []
    success = []

    for i in data:
        if i:
            url, md = i
            if not md:
                failed.append(url)
            else:
                success.append(md)
        else:
            failed.append(url)

    markdown_to_html('\n\n'.join(success), sys.argv[-1], 'Notes')

    if failed:
        print('failed:')
        for f in failed:
            print(f)
