# dropbox paper backup

Dropbox decided to not store *Dropbox Paper* Markdown files in Dropbox but somewhere else, so there's a need to backup these files!

# install & config

```
pip install -r requirements.txt
```

Create a Dropbox Developer App (https://www.dropbox.com/developers/apps) give it all the indiviual scopes permissions **then** generate an `Access token`. Add use this access token as **YOUR_API_KEY**.

# usage

```
python paper-backup.py -d ~/your/dest/folder -k YOUR_API_KEY
```

or force it, which will delete the files in the destination folder and overwrites them.

```
python paper-backup.py -f -d /your/target/folder -k YOUR_API_KEY
```

There's apparently no way to check if the (same file was already downloaded and just needs to be updated, so all your docs will be re-downloaded everytime. Sorry!
