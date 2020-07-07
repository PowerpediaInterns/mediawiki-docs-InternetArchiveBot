#!/usr/bin/env bash
# Copyright 2020 David Wong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

function installDocker() {
    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
    sudo apt update
    apt-cache policy docker-ce
    sudo apt install -y docker-ce docker-compose
    sudo systemctl status docker --no-pager
}

function installPhp() {
    sudo apt install -y php php-intl php-curl php-mysqli php-mysqlnd php-json

    # Install Composer.
    curl -sS https://getcomposer.org/installer | php
    sudo mv composer.phar /usr/local/bin/composer
    sudo chmod +x /usr/local/bin/composer
    composer
}

function installInternetarchivebot() {
    cd /opt/
    git clone https://github.com/internetarchive/internetarchivebot.git
    cd internetarchivebot/
    sudo composer install
    cd app/src/
    sudo cp "deadlink.config.docker.inc.php" "deadlink.config.local.inc.php"
    sudo gedit "deadlink.config.local.inc.php"
    cd ../../
    sudo docker-compose up -d
    sudo docker exec internetarchivebot_web_1 bash -c "cp /usr/local/etc/php/php.ini /usr/local/etc/php/php.ini.bak; sed -i 's/^\s*xdebug\.remote_enable\s*=\s*1$/xdebug.remote_autostart = 0/g' /usr/local/etc/php/php.ini"
    sudo docker-compose restart
}

installDocker
installPhp
installInternetarchivebot