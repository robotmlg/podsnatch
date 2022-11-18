# PodSnatch

PodSnatch is a simple<sup>[1](#footnote1)</sup>, cross-platform
<sup>[2](#footnote2)</sup> podcast downloader.  Feed it an OPML file and wire it
up to a cronjob, and it downloads your podcasts on your schedule.  PodSnatch
also downloads all the metadata for each episode, and stores it in a plaintext
file with the same name as the episode audio, with `.txt` appended.

<a name="footnote1">1</a>: Only \~100 lines of Python!

<a name="footnote2">2</a>: *Probably*, this has only been tested on Mac and Linux (Pop\!\_os 22.04).

## Usage

### Python

```bash
python podsnatch.py --opml <input file> -o <output directory>
```

### Pipenv

You can also use Python Pipenv to create and use virtual environments to keep your 
Python installation clean. Once `pip` is installed, run the following command to
install `pipenv`:

```bash
pip install pipenv
```

Once `pipenv` is installed, install the required packages from `Pipfile.lock`:

```bash
pipenv sync
```

To install newer versions of packages, edit `Pipfile` to the desired version then run:

```bash
pipenv update
```

To run the `podsnatch.py` script, run:

```bash
pipenv run python podsnatch.py --opml <input file> -o <output directory>
```

The `requirements.txt` can be updated based on what's in `Pipefile` by running:

```bash
pipenv requirements > requirements.txt
```

### Docker

If you don't want to deal with all the python setup crap (and I don't blame you)
you can build the docker container and run with

```bash
docker run -it -v '/path/to/opml.opml:/input.opml' -v '/path/to/output_dir:/output' podsnatch
```

If you want to limit episodes for download, use `-n` argument. Say, for download last 3 episodes, of each podcast you need specify your command to:
```bash
python podsnatch.py --opml <input file> -o <output directory> -n 3
```

## Contributing
PRs welcone!
