"""AWS Console login page HTML template."""

from datetime import datetime

# NOTE: This is a template string. Use .format(token=..., year=...) before serving.
# The {token} and {year} placeholders are filled at render time.
# All other braces are doubled (CSS/JS) to escape Python format syntax.

CONSOLE_LOGIN_PAGE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html class="a-no-js" data-19ax5a9jf="dingo" lang="en-US">
<head>
<meta charset="utf-8"/>
<title>Amazon Web Services Sign-In</title>
<meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0" name="viewport"/>
<style>
@font-face {{
  font-family: "Amazon Ember";
  src: local("Arial");
  font-weight: 400;
}}
@font-face {{
  font-family: "Amazon Ember";
  src: local("Arial-Bold");
  font-weight: 700;
}}
body, html {{
    height: 100%;
    margin: 0;
    padding: 0;
    background-color: #232f3e;
    font-family: "Amazon Ember", "Helvetica Neue", Roboto, Arial, sans-serif;
    color: #16191f;
    font-size: 14px;
    line-height: 1.4;
}}
.aws-signin-wrapper {{
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f2f3f3;
}}
.aws-signin-header {{
    text-align: center;
    padding: 24px 0;
    margin-bottom: 0;
}}
.aws-logo {{
    width: 60px;
    height: 36px;
    margin: 0 auto;
}}
/* Authentic AWS Logo (from simple-icons) */
.aws-logo-svg {{
    fill: #232F3E;
    height: 60px;
    width: 60px;
}}

.aws-signin-content {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 0 10px;
}}
.aws-signin-form {{
    background-color: #fff;
    width: 100%;
    max-width: 400px;
    border-radius: 4px;
    box-shadow: 0 1px 3px 0 rgba(0,0,0,.1);
    padding: 24px 40px;
    box-sizing: border-box;
    margin-top: 20px;
}}
h1 {{
    font-size: 20px;
    font-weight: 700;
    margin: 0 0 20px;
    color: #16191f;
}}
.form-group {{
    margin-bottom: 16px;
}}
label {{
    display: block;
    font-weight: 700;
    margin-bottom: 6px;
    color: #545b64;
    font-size: 14px;
}}
input[type="text"], input[type="password"] {{
    width: 100%;
    height: 32px;
    padding: 4px 10px;
    border: 1px solid #879596;
    border-radius: 2px;
    box-sizing: border-box;
    font-size: 14px;
    box-shadow: 0 1px 0 rgba(255,255,255,.5), 0 1px 0 rgba(0,0,0,.07) inset;
    outline: none;
    transition: all 0.1s linear;
}}
input[type="text"]:focus, input[type="password"]:focus {{
    border-color: #e77600;
    box-shadow: 0 0 3px 2px rgba(227,118,0,.5), 0 1px 0 rgba(0,0,0,.07) inset;
}}
.btn-primary {{
    background: linear-gradient(to bottom, #f7dfa5, #f0c14b);
    border-color: #a88734 #9c7e31 #846a29;
    color: #111;
    display: block;
    width: 100%;
    text-align: center;
    padding: 0;
    height: 29px;
    border-width: 1px;
    border-style: solid;
    border-radius: 2px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
    box-shadow: 0 1px 0 rgba(255,255,255,.4) inset;
}}
.btn-primary:hover {{
    background: linear-gradient(to bottom, #f5d78e, #eeb933);
}}
.btn-primary:active {{
    background: #f0c14b;
    border-color: #cdb933 #b69d30 #9c8328;
    box-shadow: 0 1px 3px rgba(0,0,0,.2) inset;
}}
.btn-text {{
    line-height: 29px;
}}
.forgot-password {{
    margin-top: 16px;
    font-size: 12px;
    text-align: right;
}}
.forgot-password a {{
    color: #007eb9;
    text-decoration: none;
}}
.forgot-password a:hover {{
    text-decoration: underline;
    color: #e47911;
}}
.aws-signin-footer {{
    text-align: center;
    padding: 30px 0;
    font-size: 11px;
    color: #545b64;
    background-color: #f2f3f3; /* Blend with body */
}}
.aws-signin-footer ul {{
    list-style: none;
    padding: 0;
    margin: 0;
}}
.aws-signin-footer li {{
    display: inline-block;
    margin: 0 8px;
}}
.aws-signin-footer a {{
    color: #007eb9;
    text-decoration: none;
}}
.aws-signin-footer a:hover {{
    text-decoration: underline;
    color: #e47911;
}}
.notice {{
    color: #545b64;
    font-size: 11px;
    margin-top: 20px;
    line-height: 1.4;
}}
.alert-box {{
    border: 1px solid #c5c5c5;
    background-color: #fff;
    padding: 14px;
    margin-bottom: 20px;
    border-radius: 4px;
    display: none;
    font-size: 13px;
}}
.user-type-selector {{
    margin-bottom: 20px;
    display: flex;
    border-bottom: 1px solid #d5dbdb;
}}
.user-type {{
    padding: 8px 0;
    margin-right: 20px;
    font-size: 14px;
    cursor: pointer;
    color: #545b64;
    font-weight: 700;
    position: relative;
}}
.user-type.active {{
    color: #16191f;
    border-bottom: 3px solid #e77600;
    margin-bottom: -2px;
}}
</style>
<script>
    function switchTab(type) {{
        document.getElementById('tab-root').classList.remove('active');
        document.getElementById('tab-iam').classList.remove('active');

        if (type === 'root') {{
            document.getElementById('tab-root').classList.add('active');
            document.getElementById('root-fields').style.display = 'block';
            document.getElementById('iam-fields').style.display = 'none';
            document.getElementById('root_email').required = true;
            document.getElementById('account').required = false;
            document.getElementById('username').required = false;
            document.getElementById('password').required = false; // Usually Next button follows, but simplified here
        }} else {{
            document.getElementById('tab-iam').classList.add('active');
            document.getElementById('root-fields').style.display = 'none';
            document.getElementById('iam-fields').style.display = 'block';
            document.getElementById('root_email').required = false;
            document.getElementById('account').required = true;
            document.getElementById('username').required = true;
            document.getElementById('password').required = true;
        }}
    }}
</script>
</head>
<body>
    <div class="aws-signin-wrapper">
        <div class="aws-signin-header">
            <svg class="aws-logo-svg" role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><title>Amazon Web Services</title><path d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.375 6.18 6.18 0 0 1-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.384-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.03-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.295.072-.583.16-.862.272a2.287 2.287 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167c.279-.144.614-.264 1.005-.36a4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.439.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.24-.024-.304-.08-.064-.048-.12-.16-.168-.311L7.586 5.55a1.398 1.398 0 0 1-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 0 1 .32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 0 1 .311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 0 1-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 0 1-.303.08h-.687c-.151 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32l-1.238-5.148-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 0 1-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.319.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 0 0 .415-.758.777.777 0 0 0-.215-.559c-.144-.151-.416-.287-.807-.415l-1.157-.36c-.583-.183-1.014-.454-1.277-.813a1.902 1.902 0 0 1-.4-1.158c0-.335.073-.63.216-.886.144-.255.335-.479.575-.654.24-.184.51-.32.83-.415.32-.096.655-.136 1.006-.136.175 0 .359.008.535.032.183.024.35.056.518.088.16.04.312.08.455.127.144.048.256.096.336.144a.69.69 0 0 1 .24.2.43.43 0 0 1 .071.263v.375c0 .168-.064.256-.184.256a.83.83 0 0 1-.303-.096 3.652 3.652 0 0 0-1.532-.311c-.455 0-.815.071-1.062.223-.248.152-.375.383-.375.71 0 .224.08.416.24.567.159.152.454.304.877.44l1.134.358c.574.184.99.44 1.237.767.247.327.367.702.367 1.117 0 .343-.072.655-.207.926-.144.272-.336.511-.583.703-.248.2-.543.343-.886.447-.36.111-.734.167-1.142.167zM21.698 16.207c-2.626 1.94-6.442 2.969-9.722 2.969-4.598 0-8.74-1.7-11.87-4.526-.247-.223-.024-.527.272-.351 3.384 1.963 7.559 3.153 11.877 3.153 2.914 0 6.114-.607 9.06-1.852.439-.2.814.287.383.607zM22.792 14.961c-.336-.43-2.22-.207-3.074-.103-.255.032-.295-.192-.063-.36 1.5-1.053 3.967-.75 4.254-.399.287.36-.08 2.826-1.485 4.007-.215.184-.423.088-.327-.151.32-.79 1.03-2.57.695-2.994z"/></svg>
        </div>
        <div class="aws-signin-content">
            <div class="aws-signin-form">
                <h1>Sign in</h1>

                <div class="user-type-selector">
                    <div id="tab-root" class="user-type" onclick="switchTab('root')">Root user</div>
                    <div id="tab-iam" class="user-type active" onclick="switchTab('iam')">IAM user</div>
                </div>

                <form method="POST" action="/console/login">
                    <input type="hidden" name="csrf_token" value="{{token}}">

                    <div id="root-fields" style="display:none;">
                        <div class="form-group">
                            <label for="root_email">Root user email address</label>
                            <input type="text" id="root_email" name="root_email">
                        </div>
                    </div>

                    <div id="iam-fields">
                        <div class="form-group">
                            <label for="account">Account ID (12 digits) or account alias</label>
                            <input type="text" id="account" name="account" required placeholder="" autofocus>
                        </div>

                        <div class="form-group">
                            <label for="username">IAM user name</label>
                            <input type="text" id="username" name="username" required>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>

                    <button type="submit" class="btn-primary">
                        <span class="btn-text">Sign in</span>
                    </button>

                    <div class="forgot-password">
                        <a href="https://signin.aws.amazon.com/forgotpassword" target="_blank" rel="noopener noreferrer">Forgot password?</a>
                    </div>
                </form>
            </div>
        </div>
        <div class="aws-signin-footer">
            <ul>
                <li><a href="https://aws.amazon.com/privacy/?nc1=f_pr" target="_blank" rel="noopener noreferrer">Privacy</a></li>
                <li><a href="https://aws.amazon.com/terms/?nc1=f_pr" target="_blank" rel="noopener noreferrer">Terms</a></li>
                <li><a href="https://aws.amazon.com/legal/cookies/" target="_blank" rel="noopener noreferrer">Cookie preferences</a></li>
            </ul>
            <div class="notice">
                &copy; 2023-{{year}}, Amazon Web Services, Inc. or its affiliates. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>"""


def render_console_login_page(token: str) -> str:
    """Render the AWS console login page with the given CSRF token."""
    return CONSOLE_LOGIN_PAGE_HTML_TEMPLATE.format(
        token=token,
        year=datetime.now().year,
    )
