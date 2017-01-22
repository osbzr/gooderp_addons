
function SelectOther(value) {
    if (value == '其他') {
        $("li.invisible_class").show();
        $("#sign_out_reason").focus();
    } else {
        $("li.invisible_class").hide();
    }}
 function json_ajax(res) {
    $.hidePreloader();
    $.showPreloader('正在签到中！')
    var url_now = $('#now_url').val();
    $.ajax({
        url: url_now,
        data: {user_id: 1, latitude: res.latitude, longitude: res.longitude},
        type: 'post',
        dataType: 'json',
        async: true,
        timeout: 10000,
        success: function (data) {
            if (data.state != 'sign_out_reason') {
                $("#span_message").html(data.message);
                  $("#latitude").val(data.latitude);
                  $("#longitude").val(data.longitude);
                  $("#sign_out_time").val(data.sign_out_time);
                $("#span_point_messge").html(data.point_messge);
                $.hidePreloader();
            } else if(data.state =='fail' || data.state =='success'){
                  $("#span_message").html(message);
                  $("#latitude").val(data.latitude);
                  $("#longitude").val(data.longitude);
                  $("#sign_out_time").val(data.sign_out_time);
                  $("#span_point_messge").html(point_messge);
            }else{
                  $("#latitude").val(data.latitude);
                  $("#longitude").val(data.longitude);
                  $("#sign_out_time").val(data.sign_out_time);
                  $("#sign_out_reason_form").show();
                  $.hidePreloader();
            }
        },
        error: function (xmlHttpRequest) {
            $.hidePreloader();
            if(XMLHttpRequest.status==500){
                var result = eval("("+XMLHttpRequest.responseText+")");
                alert(xmlHttpRequest.statusText+ xmlHttpRequest.responseText);
            }else {
                 alert('网络连接超时请检查网络连接!')
            }
        }
    })
 }
window.onload=function(){
    if (state==''){
        $.showPreloader('正在获取地理位置！')
        //json_ajax({'latitude':33.331066,'longitude':121.53426})
        wx.ready(function () {
            wx.getLocation({
                type: 'gcj02', // 默认为wgs84的gps坐标，如果要返回直接给openLocation用的火星坐标，可传入'gcj02'
                success:json_ajax,
                fail: function(res) {
                    alert('错误代码'+res.errMsg+',请联系管理员!')
                }
            })

        });
       wx.error(function(res) {
                alert('错误代码'+res.errcode+',请联系管理员!');
        })
    }else{
        // $("#sign_out_reason_form").hide();
        $("#span_message").html(message);
        $("#span_point_messge").html(point_messge);
    }
}
function check_required_input() {
    //alert('在工作时间内外出必须填写外出理由！')
    if ($("#sign_out_reason_list").val() == 'none' || ($("#sign_out_reason_list").val() == '其他' && $("#sign_out_reason").val()=='')) {
       $.toast("在工作时间内外出必须填写外出理由！");
        return false
    } else {
        return true
    }
}
