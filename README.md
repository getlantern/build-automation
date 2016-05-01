* `git clone https://github.com/getlantern/lantern.git`
* Make sure you can run `make packages`
  * `SECRET_DIR` points a directory contains `bns.pfx`
  * `security import <cert.p12> -k login.keychain -P <passphrase> -A`
* Make sure you can run `s3cmd ls`

