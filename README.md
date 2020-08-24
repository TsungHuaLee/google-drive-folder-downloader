# google-drive-folder-downloader

Download Google Drive folder without zipping!

## Getting Started

You need to enable the Drive API to use the script.
The enabling instructions can be found on [Python Quickstart](https://developers.google.com/drive/api/v3/quickstart/python).<br/>
The `credentials.json` file will be needed in the working directory.

## Basic Usage

Just run the script with target folder name and the destination path (using fill path, default value is `./DEST`) where you want to save to.

Try `python download.py -h` for more information.

### Python 3.6+

```
$ python download.py [-h] [-id] SOURCE DEST
```

