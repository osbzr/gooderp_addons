[在线试用](http://gooderp.osbzr.net/login?db=gooderp&login=admin&key=good)
======

[![Join the chat at https://gitter.im/osbzr/gooderp](https://badges.gitter.im/osbzr/gooderp.svg)](https://gitter.im/osbzr/gooderp?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Build Status](https://travis-ci.org/osbzr/gooderp.svg?branch=master)](https://travis-ci.org/osbzr/gooderp)
[![Coverage Status](https://coveralls.io/repos/github/osbzr/gooderp/badge.svg?branch=master)](https://coveralls.io/github/osbzr/gooderp?branch=master)
[![Issue Count](https://codeclimate.com/github/osbzr/gooderp/badges/issue_count.svg)](https://codeclimate.com/github/osbzr/gooderp)

开阖软件发起的开源ERP项目

如果你有一个苹果，我也有一个苹果，彼此交换后，你我还是一人一个苹果，但是如果你有一个想法，我有一个想法，彼此交换后，你我就都有两个想法，三个人呢？一百个人呢？

使用openobject框架

重写全部功能模块


Why——为什么要做GOODERP
---------------------
1、OpenERP面向最终用户，GOODERP面向实施公司

2、OpenERP项目由openerp公司主导，GOODERP项目由实施公司主导

3、提高核心功能模块的稳定性和易用性，降低标准功能部署成本

4、针对现有成熟产品重新组织功能设计，使GOODERP有清晰的市场定位和竞争对手

5、实行开源项目贡献者奖励制度，让开源成为众包

6、参照现有ERP软件构建业务伙伴支持网络和实施工具包

7、通过大量读写代码培养和发现具备openobject平台二次开发能力的程序员


What——关于GOODERP产品
--------------------
1、GOODERP是托管在github上的一个开源ERP项目

2、软件采用agpl协议，版权归代码提交者所有

3、项目范围是一组功能模块，包括财务加进销存的核心模块及满足行业特殊需求的模块

4、这些模块都以openobject8.0为平台开发

5、模块全部放在 osbzr/gooderp mater分支的根目录下，每个模块一个目录

6、参照 ys 的功能菜单和输出布局重新设计

7、项目本身不提供下载服务，上传下载均通过github版本管理工具


Who——谁来做GOODERP项目
---------------------
1、项目经理：上海开阖软件有限公司 王剑峰

2、项目投资人：GOODERP认证业务伙伴 gooderp-partner

3、项目成员：任何人均可克隆、修改、提交合并请求

4、项目经理负责协调业务伙伴与贡献者关系

5、项目投资人负责审批分支合并请求，每月评定顶尖贡献者。

6、项目成员报告bug、通过提交分支合并请求的方式向项目贡献代码


When——GOODERP项目的时间规划
--------------------------
1、项目启动日期2016年2月22日

2、第一阶段，2016年，完成财务+进销存+项目管理的核心功能

3、第二阶段，长期规划，根据客户项目和业务伙伴需求实现各行业纵深功能

4、每月定期（日期待定）举行业务伙伴会议，总结上月进度，评选最佳贡献者，计划下月工作

5、业务伙伴资格有效期为1年

6、项目实行7*24小时工作制，全年无休

7、项目以一个自然月为一个计划交付周期

Where——使用github管理GOODERP开发
-------------------------------

1、快

2、程序员最爱

3、贡献代码方便

4、免费

5、不断优化

6、一站解决

7、在线沟通协作

How——如何让GOODERP持续健康发展
-----------------------------
1、投资者应该参与决策

2、贡献者必须得到认可

3、现金回报及时到位

4、关注业务伙伴的需求，而非最终用户

5、搭建在线测试服务器

6、鼓励非程序员参与测试，特别是ys现有用户

7、开展多种双赢合作模式

开发环境准备
-------------
1.在github上fork点击右上角的fork

2.clone到本地

    git clone https://github.com/你的名字/gooderp.git
 
3.增加远程分支（也就是osbzr的分支）名为osbzr到你本地。

    git remote add osbzr https://github.com/osbzr/gooderp.git
    
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
