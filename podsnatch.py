from lxml import etree as xml
import feedparser
import requests
import argparse
import time
import re
import os


class Show:

  def __init__(self, outline_element):
    self.title = outline_element.get('title')
    self.url = outline_element.get('xmlUrl') or outline_element.get('xmlurl') or None
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
    self.url = item.enclosures[0].href if 'enclosures' in item else ''
    self.date = item.published_parsed if 'published_parsed' in item else ''

    self.show = show

  def __str__(self):
    return f"""{self.title}
{self.number}
{self.guid}
{self.date}
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


def parse_ompl(ompl_path):
  tree = xml.parse(ompl_path)
  root = tree.getroot()

  shows = root.findall('./body/outline')

  return [Show(x) for x in shows]


def save_podcasts(opml, output):
  shows = parse_ompl(opml)

  for show in shows:
    print(f'Processing show {show.title}')
    feed = feedparser.parse(show.url)

    show_path = os.path.join(output, show.get_dir_name())
    os.makedirs(show_path, exist_ok=True)

    for item in feed.entries:
      episode = Episode(item, show)

      print(f'Processing episode {episode.title}')

      full_path = os.path.join(show_path, episode.get_file_name())
      print(full_path)

      if not os.path.exists(full_path):
        print('Downloading episode')
        response = requests.get(episode.url)
        handle = open(full_path, "wb")
        handle.write(response.content)
        handle.close()

        handle = open(full_path + ".txt", "w")
        handle.write(str(episode))
        handle.close()
      else:
        print('Episode already downloaded!')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Download podcasts.')

  parser.add_argument('--opml', '-i', dest='opml_loc', action='store',
                      required=True, help='path to opml file to import')
  parser.add_argument('--output-dir', '-o', dest='output_loc', action='store',
                      required=False, default='.',
                      help='location to save podcasts')
  args = parser.parse_args()

  save_podcasts(args.opml_loc, args.output_loc)
