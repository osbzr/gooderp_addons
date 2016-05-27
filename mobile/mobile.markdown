### Mobile模块基本设置

在mobile.view中新建一条数据后在[localhost](http://localhost:8069/mobile)中会自动生成一个适应手机显示的界面

#### 字段定义
- display_name: 主页中该视图相关的菜单显示名称
- name: 该视图定义的唯一识别码，在视图中用来唯一确认相关的mobile.view配置
- model: 该视图的模型
- icon_class: 主页中菜单的icon的class，可以用来自定义相关的icon
```css
    icon_class: {
        background: url('default.png') no-repeat;
    }
```
- domain: 载入数据的时候使用的domain条件
- limit: 界面上默认列表行数，也是无限滚动的时候一次性加载的数据行数
- sequence: 主页中菜单的按照sequence从小到大排序，默认为16
- arch: 实际视图中界面定义

#### arch定义
在arch中所有的自定义视图必须定义在mobile标签中
- mobile标签中存在四种字段定义
- name属性指定model中的字段(**name属性必须存在model的字段定义中**)
- string属性指定该字段在界面上的标题
- 每个field标签都必须存在name和string属性

- ##### tree 视图
```xml
<tree>
    <field name='field' string='string' aggregate='sum' />
</tree>
```
- 在tree视图中field标签强制为3个，分别定义到界面列表中的左、中、右三个字段
- 使用aggregate属性来指定float、integer字段类型的聚合函数（sum、avg、max、min）


- #### form 视图
```xml
<form>
    <field name='field' string='string' />
</form>
```
- 在from视图中field标签数量不限制，可以自定义任意个field标签

- #### search 视图
```xml
<search>
    <field name='field' string='string' operator=">" />
</search>
```
- 搜索视图会显示在搜索框的下拉列表中
- 可以定义一个operator的字段,用来自定义默认操作符(**暂时只支持数字的操作符**)
- operator字段可选的值为:
    ```python
    MAP_OPERATOR = {
        '>': u'大于', '<': u'小与', '>=': u'大于等于',
        '<=': u'小与等于', '=': u'等于', '!=': u'不等于',
    }
    ```
- #### wizard 视图
```xml
<wizard>
    <field name='name' string='string' type='many2one' model='model' domain="[('column', '=', 'column')]" />
    <field name='name' string='string' type='char' placeholder='placeholder' required='1' />
    <field name='name' string='string' type='selection' selection="[('option', 'option')]" />
</wizard>
```
- 每当在arch中定义了一个wizard的子视图后，会在进入列表界面中首先自动打开一个向导界面
- 在向导中输入的值会被作为context传入到列表中去
- 当需要向导的时候，可以自定义model的search_read函数来自定义接收context里面的参数
    > 在context中普通字段会被设置为{name: value}，其中name是在field标签中定义的值，value是向导中收集的值

    > 在context中many2one字段会被设置为{name: [id, value]}，其中id是被选择的many2one字段的实际id

- 可以使用一个required的属性来指示在向导中这个字段必输
- wizard中定义的每个字段都要设置type属性
- 当type属性为many2one时，需要定义一个model属性，指定该field的模型，还可以设置一个domain来作为输入的时候的domain条件
- 当type属性为selection的时候，需要定义一个selection属性，来指定向导中该字段的选择值
- wizard中的定义字段的type属性可选值为:
    ```python
    WIZARD_TYPE = [
        'many2one', 'number', 'date',
        'datetime', 'char', 'text', 'selection'
    ]    ```
