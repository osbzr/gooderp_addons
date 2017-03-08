[【在线试用】](http://demo.gooderp.org:8888)
或
[【下载Windows绿色版】](http://com.osbzr.net/osbzr_downloads/static/gooderp.zip)
----
[![Join the chat at https://gitter.im/osbzr/gooderp](https://badges.gitter.im/osbzr/gooderp.svg)](https://gitter.im/osbzr/gooderp?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.svg)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
[![Build Status](https://travis-ci.org/osbzr/gooderp_addons.svg?branch=master)](https://travis-ci.org/osbzr/gooderp_addons)
[![Coverage Status](https://coveralls.io/repos/github/osbzr/gooderp_addons/badge.svg?branch=master)](https://coveralls.io/github/osbzr/gooderp_addons?branch=master)
[![Issue Count](https://codeclimate.com/github/osbzr/gooderp_addons/badges/issue_count.svg)](https://codeclimate.com/github/osbzr/gooderp_addons)

开发环境准备
-------------
1.在github上fork点击右上角的fork

2.clone到本地

    git clone https://github.com/你的名字/gooderp_addons.git
    
3.切换到gooderp_addons项目目录

    cd gooderp_addons/
    
4.增加远程分支（也就是osbzr的分支）名为osbzr到你本地。

    git remote add osbzr https://github.com/osbzr/gooderp_addons.git
    
环境就准备好了


把远程分支的合并到自己的分支
----------------------------
1.把对方的代码拉到你本地。

    git fetch osbzr

2.合并对方代码

    git merge osbzr/master

3.最新的代码推送到你的github上。

    git push origin master
    
当本地代码写好要提交到主干项目
-------------------------------
1.添加要提交的目录
    
    git add .
    
2.提交更新

    git commit -m"本次修改的描述"
    
3.推送到github

    git push
    
4.在github上点击pull request按钮
