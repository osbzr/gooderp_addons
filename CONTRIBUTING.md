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
