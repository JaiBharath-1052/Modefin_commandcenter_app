email_templates = {
    'user_verification_template':{
        "subject":"Modefin verification email for CHATBOT Platform",
        "message":'''<h1>Hello. This is Modefin User Verification for Chat bot platform. </h1>
                    <br>
                    <p>Please verify us that the account is yours by clicking the given button below.</p>
                    <br>
                    <a href="{}">
                        <button>YES. It's Me</button>
                    </a> 
                '''
    },
    
    'password_reset_template':{
        "subject":"Modefin reset password link for CHATBOT Platform",
        "message":'''<h1>Hello. This is Modefin reset password link for Chat bot platform. </h1>
                    <br>
                    <p>Please click the below link and reset your password</p>
                    <br>
                    <p>Reset link :</p>
                    <a href="{}">{}</a>
                '''
    },
    
    'invitation_link_template':{
        "subject":"Modefin Invitation for CHATBOT Platform",
        "message":'''<h1>Hello. This is Modefin Invitation for Chat bot platform. </h1>
                    <br>
                    <p>You have been invited for the role {}. Please login with the below given link</p>
                    <br>
                    <p>Registration link :</p>
                    <a href="{}">{}</a>
                '''
    },
    
    'customer_transcript_template':{
        "subject":"TRANSCRIPT FROM MODEFIN FOR YOUR CONVERSATION",
        "message":'''<h1>CHAT TRANSCRIPT FROM OUR BACKEND TO THE CUSTOMER</h1>
                    <br>
                    <h5>SENDER NAME : </h5> <p>{}</p>
                    <h5>SENDER EMAIL : </h5> <p>{}</p>

                    <br><br><br>
                    <h1>CHAT TRANSCRIPT</h1>
                    <p>Here we will send the chats of that user</p>
                '''
    },
    
    'send_email_notification_template':{
        "subject":"You have got new conversation!",
        "message":'''<h1>Hello! You have been assigned some conversation from the customer. Please attend!</h1>
                    <br>
                    {}
                '''
    },
    
    'fallback_email_template':{
        "subject":"You have some message un-attended. Please attend!",
        "message":'''<h1>Hello! You have got some unattend  message from the customer. Please reply!</h1>
                    <br>
                    {}
                '''
    }
    
}

