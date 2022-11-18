#! /usr/bin/env python

from lxml import etree as xml
from tqdm import tqdm
from mutagen.easyid3 import EasyID3
from datetime import datetime
import feedparser
import requests
import argparse
import signal
import time
import sys
import re
import os

TMP_EXT = '.part'


class Show:

  def __init__(self, outline_element):
    self.url = (outline_element.get('xmlUrl') or
                outline_element.get('xmlurl') or
                None)
    self.title = (outline_element.get('title') or
                  outline_element.get('text')[0:50] or
                  self.url.split('/')[-1])
    self.episode_guids = []

  def __str__(self):
    return f'{self.title}: {self.url}'

  def get_dir_name(self):
    return re.sub(r'[\W]+', '_', self.title)


class Episode:

  def __init__(self, item, show):
    self.guid = item.id if 'id' in item else ''
    self.title = item.title if 'title' in item else ''
    self.link = item.link if 'link' in item else ''
    self.description = item.summary if 'summary' in item else ''
    self.content = item.content[0].value if 'content' in item else ''
    self.number = item.itunes_episode if 'itunes_episode' in item else ''
    self.season = item.itunes_season if 'itunes_season' in item else ''
    self.url = item.enclosures[0].href if 'enclosures' in item and item.enclosures else ''
    self.date = item.published_parsed if 'published_parsed' in item else ''
    self.date_text = item.published if 'published' in item else ''

    self.show = show

  def __str__(self):
    return f"""{self.title}
{self.season}:{self.number}
{self.guid}
{self.date_text}
{self.link}
{self.url}
{self.content if self.content else self.description}
{self.description}"""

  def get_file_name(self):
    url_tail = self.url.split('/')[-1].split('?')[0]
    show_title = re.sub(r'[\W]+', '_', self.show.title)
    ep_title = re.sub(r'[\W]+', '_', self.title)
    formatted_date = time.strftime('%Y_%m_%d', self.date)

    name_tokens = [formatted_date, self.number, ep_title, url_tail]
    return '_'.join([s for s in name_tokens if s is not ''])


def parse_opml(opml_path):
  tree = xml.parse(opml_path)
  root = tree.getroot()

  shows = root.findall('./body/outline')

  return [Show(x) for x in shows]


def download(url, path, mode):
  # https://stackoverflow.com/a/37573701
  response = requests.get(url, stream=True)
  total_size = int(response.headers.get('content-length', 0))
  block_size = 1024

  downloaded_size = 0
  t = tqdm(total=total_size, unit='iB', unit_scale=True)
  with open(path, mode) as f:
    for data in response.iter_content(block_size):
      t.update(len(data))
      f.write(data)
      downloaded_size += len(data)
  t.close()

  if total_size != 0 and t.n != total_size:
    print("ERROR downloading file")

  return downloaded_size

total_downloaded_size = 0
total_downloaded = 0
full_path = ''


def convert_to_size(size):
  """
  Takes a number of bytes and converts it to a string that is a human readable size.
  """
  size_labels = ['B','KB','MB','GB','TB', 'PB', 'EB', 'ZB', 'YB']
  converted_size = size
  counter = 0
  while converted_size > 1000:
    converted_size /= 1000
    counter += 1
  
  size_str = f'{converted_size:.2f}{size_labels[counter]}'

  return size_str


def save_podcasts(opml, output, episode_count=None):
  global total_downloaded_size
  global total_downloaded
  global full_path

  shows = parse_opml(opml)

  for show in shows:
    print(f'Processing show {show.title}')
    feed = feedparser.parse(show.url)

    show_path = os.path.join(output, show.get_dir_name())
    os.makedirs(show_path, exist_ok=True)

    cnt_eps_to_dl = (int(episode_count, 10)
                     if episode_count is not None
                     else len(feed.entries))

    i = 0
    show_downloaded = 0
    while show_downloaded < cnt_eps_to_dl and i < len(feed.entries):
      item = feed.entries[i]
      episode = Episode(item, show)

      print(f'Processing episode {episode.title}')

      full_path = os.path.join(show_path, episode.get_file_name())
      print(full_path)

      if not os.path.exists(full_path) and episode.url:
        print('Downloading episode')
        total_downloaded_size += download(episode.url, full_path + TMP_EXT, 'wb')

        os.rename(full_path + TMP_EXT, full_path)

        try:
          add_id3_tags(full_path, show, episode)
        except:
          print(f'Episode saved at {full_path} does not support ID3 tags.')

        handle = open(full_path + ".txt", "w")
        handle.write(str(episode))
        handle.close()

        show_downloaded += 1
        total_downloaded += 1
      else:
        print('Episode already downloaded!')


      i += 1

    print(f'{total_downloaded} episode(s) totaling {convert_to_size(total_downloaded_size)} downloaded')


def add_id3_tags(filepath, show=None, episode=None):
  """
  Add ID3 tags to audio files where not already present. Information added to tags
  will be based on Show and Episode information provided.
  """
  # print(EasyID3.valid_keys.keys()) # Prints all keys in EasyID3. This is a reduced number due to being able to handle many versions of IDv3.
  tags = EasyID3(filepath)

  # ID3 Tags based on Episode info
  if episode is not None:
    add_retrieved_tag(tags, episode.season, 'discnumber')
    add_retrieved_tag(tags, episode.number, 'tracknumber')
    add_retrieved_tag(tags, episode.title, 'title')
    add_retrieved_tag(tags, episode.url, 'website')

    format = "%a, %d %b %Y %H:%M:%S %z"
    episode_datetime = datetime.strptime(episode.date_text, format)
    add_retrieved_tag(tags, str(episode_datetime.year), 'date')

  # ID3 Tags based on Show info
  if show is not None:
    add_retrieved_tag(tags, show.title, 'artist')

  add_retrieved_tag(tags, 'Podcast', 'genre')

  # ID3 Tags based on other Tags
  add_dependant_tag(tags, 'title', 'titlesort')
  add_dependant_tag(tags, 'artist', 'artistsort')
  add_dependant_tag(tags, 'artist', 'album')
  add_dependant_tag(tags, 'artist', 'author')
  add_dependant_tag(tags, 'artist', 'albumartist')
  add_dependant_tag(tags, 'album', 'albumsort')
  add_dependant_tag(tags, 'albumartist', 'albumartistsort')
  add_dependant_tag(tags, 'date', 'originaldate')
  
  tags.save()

def add_retrieved_tag(tags, info, dest_tag):
  """
  Add specific informtion to a tag if the tag is not present or unused and info was provided.
  """
  if (dest_tag not in tags or tags[dest_tag] == '') and info != '':
    tags[dest_tag] = info

def add_dependant_tag(tags, src_tag, dest_tag):
  """
  Add one tags information to another tag.
  """
  if (dest_tag not in tags or tags[dest_tag] == '') and src_tag in tags:
    tags[dest_tag] = tags[src_tag]

def ctrl_c_handler(signum, frame):
  print('Stopping...')

  if os.path.exists(full_path + TMP_EXT):
    os.remove(full_path + TMP_EXT)

  print(f'{total_downloaded} episode(s) totaling {convert_to_size(total_downloaded_size)} downloaded')
  sys.exit(1)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download podcasts.')

  parser.add_argument('--opml', '-i', dest='opml_loc', action='store',
                      required=True, help='path to opml file to import')
  parser.add_argument('--output-dir', '-o', dest='output_loc', action='store',
                      required=False, default='.',
                      help='location to save podcasts')
  parser.add_argument('--number-of-episodes', '-n', dest='ep_cnt',
                      action='store', default=None,
                      help='how many episodes to download. By default - download all')
  args = parser.parse_args()

  signal.signal(signal.SIGINT, ctrl_c_handler)

  save_podcasts(args.opml_loc, args.output_loc, args.ep_cnt)
