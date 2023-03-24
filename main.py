import argparse
import os
import requests
import re
from clint.textui import progress
from bs4 import BeautifulSoup
import logging
from pathlib import Path

args = dict()


def find_meta_from_url(url):
    meta_info = dict()
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    input_tag = soup.find('input', {'name': 'mediaId'})
    media_id = input_tag['value']
    meta_tag = soup.find('meta', attrs={'property': 'og:title'})
    content = meta_tag.get('content')
    meta_info['media_id'] = media_id
    meta_info['name'] = content
    return meta_info


def download_file(mediaId, chunk_size=1024 * 8, host="download3.vimm.net", referer="https://vimm.net/",
                  user_agent="User-Agent: Mozilla/5.0"):
        with requests.get(f"https://{host}/download/",
                          stream=True,
                          params={"mediaId": str(mediaId)},
                          headers={"User-Agent": user_agent,
                                   "Host": host,
                                   "Referer": referer}) as r:
            r.raise_for_status()

            d = r.headers['content-disposition']
            local_filename = re.findall("filename=(.+)", d)[0]
            local_filename = local_filename.translate({ord(i): None for i in "\"'"})
            print(local_filename)
            info("Downloading " + str(local_filename))
            full_download_path = args.outfolder
            if not os.path.exists(full_download_path):
                os.makedirs(full_download_path)
            with open(full_download_path + local_filename, 'wb') as f:
                total_length = int(r.headers.get('content-length'))
                for chunk in progress.bar(r.iter_content(chunk_size=chunk_size),
                                          expected_size=(total_length / chunk_size) + 1):
                    f.write(chunk)
        return local_filename


def parse_input(filename):
    with open(filename) as download_queue:
        download_list = download_queue.read()
        queue = list()
        for each in download_list.split():
            if each[0] != '#':
                download_entry = dict()
                download_entry['url'] = each
                meta_info = find_meta_from_url(download_entry['url'])
                download_entry['name'] = meta_info['name']
                download_entry['media_id'] = meta_info['media_id']
                queue.append(download_entry)
                info("Added " + download_entry['url'] + " " + download_entry['name'] + " to queue.")
        return queue


def setup_logging():
    logfile = args.logfile
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG

    logging.basicConfig(filename=logfile, encoding='utf-8', level=level, filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")


def info(*args, **kwargs):
    logging.info(*args, **kwargs)


def get_commandline_arguments():
    parser = argparse.ArgumentParser(
        prog="vimmDownloadManager",
        description="Downloads files from vimm.net"
    )
    parser.add_argument('-u', '--url', help='a single url to download')
    parser.add_argument('-i', '--infile', help='input file consisting of vimm.net urls one in each line',
                        default='list.txt')
    parser.add_argument('-o', '--outfolder', help='where to put downloaded files',
                        default=str(Path.home() / "Downloads") + '\\vdmDownloads\\')
    parser.add_argument('-l', '--logfile', help='where to log actions', default='vdm.log')
    parser.add_argument('-d', '--debug', action='store_true', help='enables DEBUGING lines in logs')
    global args
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    get_commandline_arguments()
    setup_logging()
    if args.url is not None:
        meta_info = find_meta_from_url(args.url)
        download_file(meta_info['media_id'])
        exit()
    input_file = args.infile
    queue = parse_input(input_file)
    for download_entry in queue:
        download_hosts = ["download3.vimm.net", "download5.vimm.net"]
        while len(download_hosts) != 0:
            try:
                download_file(download_entry['media_id'], host=download_hosts.pop())
                break
            except:
                pass