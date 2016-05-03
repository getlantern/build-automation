Script to check for updates of release branches of Lantern repo, build and upload automatically, then notify through Slack channel.

==To setup on Mac:

* Preparing environment
```
# Install Homebrew
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
# Install/update required packages
brew install Caskroom/cask/virtualbox docker-machine docker python go nodejs s3cmd
pip install pyyaml
npm install -g appdmg svgexport
# Create docker-machine. Be sure to provide large enough disk and sufficient cpu/memory.
docker-machine create default --driver virtualbox --virtualbox-disk-size 40000 --virtualbox-memory 3072 --virtualbox-cpu-count 3
```

* `git clone https://github.com/getlantern/lantern.git`

* Import certs to sign Mac binary and installer.
  `sudo security import <cert.p12> -k "/Library/Keychains/System.keychain" -P <passphrase> -A`

* `SECRET_DIR` points a directory contains `bns.pfx` and `bns_cert.p12`.

* `BNS_CERT_PASS` is exported

* `SLACK_WEBHOOK_PATH` is exported, which is the absolute path after `https://hooks.slack.com` in the webhook url.

* [`s3cmd`](http://s3tools.org/usage) is properly configured
