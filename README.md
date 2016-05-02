Script to check for updates of release branches of Lantern repo, build and upload automatically, then notify through Slack channel.

Prerequisites

* `git clone https://github.com/getlantern/lantern.git`

* Make sure you can run at least `make package-windows package-linux`

  * `SECRET_DIR` points a directory contains `bns.pfx`

  * `security import <cert.p12> -k login.keychain -P <passphrase> -A` (on Mac, if you want to also build Mac installer)

* [`s3cmd`](http://s3tools.org/usage) properly configured

