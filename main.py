from typing import Union
from fastapi import FastAPI, APIRouter, Request, Depends, Response, Header, Cookie, Query, WebSocket, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload

# JWT imports
from serializers import SettingsSerializer
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.middleware.cors import CORSMiddleware

# Routers
from ws.routers import wsroutes  # This is a list of routes
from ws.routers import router as ws_router

import settings

from models import *
from sqlalchemy import select

from fastapi.staticfiles import StaticFiles


app = FastAPI()

from views import awayMode, awayModeUpdation, createUser, home, emailVerification, forgotPassword, createToken, logout
from views import refreshToken,showProfile,profileDataUpdation,profilePhotoUpdation,emailUpdation,passwordUpdation
from views import notificationPreferences, emailNotificationUpdation, browserNotificationUpdation
from views import companyDetails, companyDetailsUpdation, domainUrlUpdation,editTag
from views import teammates, deleteTeammate, changeRole, inviteTeammate,resendInvitation,invitedTeammateDeletion
from views import registerInvitedTeammate, createTeam, editTeam, deleteTeam, addTeamMembers, removeTeammate, addBotToTeam
from views import removeBot, showCsatRatings, csatRatingsUpdation, showFallbackEmails, fallbackEmailsUpdation
from views import conversationRules,assignConversation,allowConvReassignment,botRoutingRules
from views import humanRoutingRules,waitingQueueStatus,enableWaitingQueue,maxConcurrentChatsUpdation
from views import autoResolve,autoResolveUpdation,convTranscript,convTranscriptCompany,convTranscriptUser
from views import quickReplies,addQuickReply,editQuickReply,deleteQuickReply,pseudonym,pseudonymUpdation
from views import chatWidgetCustomization,chatWidgetStyling,chatNotificationSound,chatWidgetBranding,chatWidgetConfig
from views import secureChatwidget,botReplyDelay,singleThreadConv,disableChatWidget,domainRestriction
from views import textToSpeech,speechToText,hideAttachment,greetingMessage,enableGreetingMessage,editGreetingMessage
from views import preChatLeadCollection,enablePreChatLeadCollection,preChatHeading,addPreChatCustomField
from views import editPreChatCustomField,deletePreChatCustomField,awayMessage,showAwayMessage,collectEmailFromAnonymous
from views import awayMessageForKnown,awayMessageForUnknown,welcomeMessage,showWelcomeMessage,collectEmailForWelcomeMsg
from views import addWelcomeMsgCategory,deleteWelcomeMsgCategory,addWelcomeMessage,editWelcomeMessage
from views import deleteWelcomeMessage,showHelpCenterCategories,addHelpCenterCategory,editHelpCenterCategory
from views import deleteHelpCenterCategory,emptyHelpCenterArticle,singleHelpCenterCategory,showHelpCenterArticle
from views import addHelpCenterArticle,editHelpCenterArticle,deleteHelpCenterArticle,helpCenterCustomization
from views import helpCenterAppearanceUpdation,helpCenterCustomDomainUrl,dialogflowESBotIntegration,manageAllBots
from views import dialogflowCXBotIntegration,customPlatformBotIntegration,dialogflowCXSetupEdition
from views import showSingleBot,deleteBot,editBotProfile,editBotHumanHandoff,dialogflowESSetupEdition
from views import customPlatformSetupEdition,allCustomers,deleteCustomer,blockCustomer
from views import addCustomerEmail,addCustomerRealname,addCustomerPhoneNumber,allConversations,singleConversation
from views import addConversationTag,removeConversationTag,conversationStatus,allTags,removeTags
from views import takeOverConversation,sendTranscriptToCustomer,convFilterOptions,addTag,getAppId
from views import filtered_conversations,resetForgotPassword,customerConversations,getCurrentCustomer
from views import resolvedConversations,addCsatRating,chatWidgetPopupSettings,WelcomeMessageCRud
from views import showOperatorPermissions,allowConvAssignmentToTeammates,allowConvAssignmentToBot
from views import logfiles,singleLogfile,checkAvailablityStatus,changeAvailablityStatus,allowConvAssignmentToTeam
from views import currently_available_agent_list, changeConvOpenedStatus ,frontEndChatWidgetSettings,autoResolveMessageUpdation,dashboard_page


from app_log.logModule import log_message
from tasks import sendEmailNotificationTask, sendFallbackEmailTask, sendEmails


# TODO: Chat api
# TODO: logout

origins = ["*"]
 
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/chui4.01", StaticFiles(directory="chui4.01"), name="chat") # RemProd Remove in production
# app.mount("D:/New Products/Chatbot/chdashboard/Chat-bot deployment/chui4.01", StaticFiles(directory="chui4.01"), name="chat") # RemProd Remove in production



# JWT
@AuthJWT.load_config
def get_config():
    return SettingsSerializer()


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# Cookies for Websocket
async def get_cookie_or_token(
    websocket: WebSocket,
    session: Union[str, None] = Cookie(default=None),
    token: Union[str, None] = Query(default=None),):
    if session is None and token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


# Register Router
router = APIRouter()

# Testing url
router.get('/')(home)



#User registration and login
router.post('/api/user/create')(createUser)
router.get('/api/user/verification/{code}')(emailVerification)
router.post('/api/token')(createToken) # Username & Password
router.post('/api/token/refresh')(refreshToken) # Access token required
router.post('/api/logout')(logout) # Access token required
router.post('/api/user/forgot-password')(forgotPassword) 
router.post('/api/user/reset-password/{token}')(resetForgotPassword)

#Availablity Status
router.get('/api/availability-status')(checkAvailablityStatus)
router.post('/api/availability-status')(changeAvailablityStatus)


#Settings/Personal/Profile
router.get('/api/settings/profile')(showProfile)# Refresh token required
router.post('/api/settings/profile-data-updation')(profileDataUpdation)# Refresh token required
router.post('/api/settings/profile-photo-updation')(profilePhotoUpdation)# Refresh token required
router.post('/api/settings/email-updation')(emailUpdation)# Refresh token required
router.post('/api/settings/password-updation')(passwordUpdation)# Refresh token required




# Settings/Personal/Notification Preferences
router.get('/api/settings/notification-preferences')(notificationPreferences)# Refresh token required
router.post('/api/settings/email-notification')(emailNotificationUpdation)# Refresh token required
router.post('/api/settings/browser-notification')(browserNotificationUpdation)# Refresh token required




# Settings/ Company / General
router.get('/api/settings/company-details')(companyDetails)# Refresh token required
router.post('/api/settings/company-details-updation')(companyDetailsUpdation)# Refresh token required
router.post('/api/settings/domain-url-updation')(domainUrlUpdation)# Refresh token required



# Settings / Company / Teammates
router.get('/api/settings/teammates')(teammates)# Refresh token required
router.post('/api/settings/change-role')(changeRole)# Refresh token required
router.delete('/api/settings/delete-teammate')(deleteTeammate)# Refresh token required
router.post('/api/settings/invite-teammate')(inviteTeammate)# Refresh token required
router.post('/api/settings/resend-invitation')(resendInvitation)# Refresh token required
router.delete('/api/settings/delete-invited-teammate')(invitedTeammateDeletion)# Refresh token required
router.post('/api/settings/register-invited-teammate/{token}')(registerInvitedTeammate)# Refresh token required
router.post('/api/settings/create-team')(createTeam)# Refresh token required
router.patch('/api/settings/edit-team')(editTeam)# Refresh token required
router.delete('/api/settings/delete-team')(deleteTeam)# Refresh token required
router.post('/api/settings/add-teammembers')(addTeamMembers)# Refresh token required
router.post('/api/settings/remove-teammate')(removeTeammate)# Refresh token required
router.post('/api/settings/add-bot-to-team')(addBotToTeam)# Refresh token required
router.post('/api/settings/remove-bot-from-team')(removeBot)# Refresh token required



# Settings / Company / CSAT Ratings
router.get('/api/settings/csat-ratings')(showCsatRatings) 
router.post('/api/settings/csat-ratings')(csatRatingsUpdation) 



# Settings / Company / Fallback Emails
router.get('/api/settings/fallback-emails')(showFallbackEmails) 
router.post('/api/settings/fallback-emails')(fallbackEmailsUpdation)

# Settings /  Company / Operator Permissions
router.get('/api/settings/operator-permissions')(showOperatorPermissions)
router.post('/api/settings/operator-permissions/assign-conv-to-teammates')(allowConvAssignmentToTeammates)
router.post('/api/settings/operator-permissions/assign-conv-back-to-bot')(allowConvAssignmentToBot)
router.post('/api/settings/operator-permissions/reassign-conv-to-another-team')(allowConvAssignmentToTeam)
                                                            

# Settings / Conversations /  Rules
router.get('/api/settings/conversation-rules')(conversationRules)
router.post('/api/settings/assign-conversation')(assignConversation)
router.post('/api/settings/bot-routing-rules')(botRoutingRules)
router.post('/api/settings/human-routing-rules')(humanRoutingRules)
router.post('/api/settings/conversation-reassignment')(allowConvReassignment)



# Settings / Conversations / Waiting queue
router.get('/api/settings/waiting-queue')(waitingQueueStatus)
router.post('/api/settings/waiting-queue-updation')(enableWaitingQueue)
router.post('/api/settings/waiting-queue-max-chats')(maxConcurrentChatsUpdation) #for waiting queue


# Settings / Conversations / Auto Resolve
router.get('/api/settings/auto-resolve')(autoResolve)
router.post('/api/settings/auto-resolve-updation')(autoResolveUpdation)
router.post('/api/settings/auto-resolve-message-updation')(autoResolveMessageUpdation)


# Settings / Conversations / Chat Transcript
router.get('/api/settings/conversation-transcript')(convTranscript)
router.post('/api/settings/conversation-transcript-company-updation')(convTranscriptCompany)
router.post('/api/settings/conversation-transcript-user-updation')(convTranscriptUser)


# Settings / Conversations / Quick Replies
router.get('/api/settings/quick-replies')(quickReplies)
router.post('/api/settings/quick-replies')(addQuickReply)
router.patch('/api/settings/quick-replies')(editQuickReply)
router.delete('/api/settings/quick-replies')(deleteQuickReply)



# Settings / Conversations / Pseudonyms
router.get('/api/settings/pseudonym')(pseudonym)
router.post('/api/settings/pseudonym')(pseudonymUpdation)



# Settings / Conversations / Tags
router.post('/api/settings/tags')(addTag)
router.get('/api/settings/tags')(allTags)
router.delete('/api/settings/tags')(removeTags)
router.patch('/api/settings/tags')(editTag)



# Settings / Chat Widget / Customization
router.get('/api/settings/chat-widget-customization')(chatWidgetCustomization)
router.post('/api/settings/chat-widget-branding')(chatWidgetBranding)
router.post('/api/settings/chat-widget-styling')(chatWidgetStyling)
router.post('/api/settings/chat-notification-sound')(chatNotificationSound)


# Settings / Chat Widget / Configuration
router.get('/api/settings/chat-widget-configuration')(chatWidgetConfig)
router.post('/api/settings/secure-chat-widget')(secureChatwidget)
router.post('/api/settings/bot-reply-delay')(botReplyDelay)
router.post('/api/settings/single-thread-conversation')(singleThreadConv)
router.post('/api/settings/disable-chat-widget')(disableChatWidget)
router.post('/api/settings/domain-restrictions')(domainRestriction)
router.post('/api/settings/text-to-speech')(textToSpeech)
router.post('/api/settings/speech-to-text')(speechToText)
router.post('/api/settings/hide-attachment')(hideAttachment)



# Settings / Chat Widget / Greeting Message
router.get('/api/settings/greeting-message')(greetingMessage)
router.post('/api/settings/enable-greeting-message')(enableGreetingMessage)
router.post('/api/settings/edit-greeting-message')(editGreetingMessage)



# Settings / Chat Widget / Pre chat lead collection
router.get('/api/settings/pre-chat-lead-collection')(preChatLeadCollection)
router.post('/api/settings/enable-pre-chat-lead-collection')(enablePreChatLeadCollection)
router.post('/api/settings/pre-chat-lead-heading')(preChatHeading)
router.post('/api/settings/add-pre-chat-custom-field')(addPreChatCustomField)
router.patch('/api/settings/edit-pre-chat-custom-field')(editPreChatCustomField)
router.delete('/api/settings/delete-pre-chat-custom-field')(deletePreChatCustomField)



# Settings / Chat Widget / Away message
router.get('/api/settings/away-message')(awayMessage)
router.post('/api/settings/show-away-message')(showAwayMessage)
router.post('/api/settings/collect-email-for-away-message')(collectEmailFromAnonymous)
router.post('/api/settings/away-message-for-known')(awayMessageForKnown)
router.post('/api/settings/away-message-for-unknown')(awayMessageForUnknown)



# Settings / Chat Widget / Welcome message
router.get('/api/settings/welcome-message')(welcomeMessage)
router.post('/api/settings/show-welcome-message')(showWelcomeMessage)
router.post('/api/settings/collect-email-for-welcome-message')(collectEmailForWelcomeMsg)
router.post('/api/settings/add-welcome-message-language-category')(addWelcomeMsgCategory)
router.delete('/api/settings/delete-welcome-message-language-category')(deleteWelcomeMsgCategory)
router.post('/api/settings/add-welcome-message')(addWelcomeMessage)
router.patch('/api/settings/edit-welcome-message')(editWelcomeMessage)
router.delete('/api/settings/delete-welcome-message')(deleteWelcomeMessage)
router.post('/api/settings/add-edit-welcome-messages')(WelcomeMessageCRud)


# Profile / Away Mode
router.get('/api/profile/away-mode')(awayMode)
router.post('/api/profile/away-mode')(awayModeUpdation)


# Help Center / Content
router.get('/api/help-center/categories')(showHelpCenterCategories)
router.post('/api/help-center/categories')(addHelpCenterCategory)
router.patch('/api/help-center/categories')(editHelpCenterCategory)
router.delete('/api/help-center/categories')(deleteHelpCenterCategory)
router.get('/api/help-center/categories/{category_id}')(singleHelpCenterCategory)
router.get('/api/help-center/empty-article')(emptyHelpCenterArticle)
router.get('/api/help-center/article')(showHelpCenterArticle)
router.post('/api/help-center/article')(addHelpCenterArticle)
router.patch('/api/help-center/article')(editHelpCenterArticle)
router.delete('/api/help-center/article')(deleteHelpCenterArticle)


# Help Center / Customization
router.get('/api/help-center/customization')(helpCenterCustomization)
router.post('/api/help-center/appearance-and-settings-updation')(helpCenterAppearanceUpdation)
router.post('/api/help-center/custom-domain-url-updation')(helpCenterCustomDomainUrl)



#----------------------------------- BOT INTEGRATIONS ------------------------------------------------

router.get('/api/bot-integration/manage-all-bots')(manageAllBots)
router.get('/api/bot-integration/manage-all-bots/{bot_id}')(showSingleBot)
router.delete('/api/bot-integration/manage-all-bots/{bot_id}')(deleteBot)
router.post('/api/bot-integration/bot-profile-updation')(editBotProfile)
router.post('/api/bot-integration/bot-human-handoff-updation')(editBotHumanHandoff)

# Bot integration
router.post('/api/bot-integration/dialogflow-es')(dialogflowESBotIntegration)
router.patch('/api/bot-integration/dialogflow-es')(dialogflowESSetupEdition)
router.post('/api/bot-integration/dialogflow-cx')(dialogflowCXBotIntegration)
router.patch('/api/bot-integration/dialogflow-cx')(dialogflowCXSetupEdition)
router.post('/api/bot-integration/custom-platform')(customPlatformBotIntegration)
router.patch('/api/bot-integration/custom-platform')(customPlatformSetupEdition)


# Customers
router.get('/api/customers')(allCustomers)
router.delete('/api/delete-customer')(deleteCustomer)
router.post('/api/block-customer')(blockCustomer)



# Conversations
router.get('/api/conversations/agent-list')(currently_available_agent_list)
router.get('/api/conversations/all-conversations')(allConversations)
router.get('/api/conversations/resolved-conversations')(resolvedConversations)
router.get('/api/conversations/all-conversations/{conversation_id}')(singleConversation)
router.post('/api/conversations/add-customer-email')(addCustomerEmail)
router.post('/api/conversations/add-customer-name')(addCustomerRealname)
router.post('/api/conversations/add-customer-phone')(addCustomerPhoneNumber)
router.post('/api/conversations/conversation-tag')(addConversationTag)
router.delete('/api/conversations/conversation-tag')(removeConversationTag)
router.patch('/api/conversations/conversation-status')(conversationStatus)
# router.post('/api/conversations/assign-conversation-to-agent')(assignConversationToAgent)
router.post('/api/conversations/take-over-conversation')(takeOverConversation)
router.post('/api/conversations/send-transcript-to-customer')(sendTranscriptToCustomer)
router.get('/api/conversations/conversation-filter-options')(convFilterOptions)
router.get('/api/conversations/filtered-conversations')(filtered_conversations)


# FRONT END
router.post('/api/customer_conversations/{customer_id}')(customerConversations)
router.post('/api/change-conv-opened-status')(changeConvOpenedStatus)
router.get('/api/current_customer')(getCurrentCustomer)
router.post('/api/add_csat_rating')(addCsatRating)
router.get('/api/chat-widget-popup-settings')(chatWidgetPopupSettings)
router.get('/api/frontend-chat-widget-settings')(frontEndChatWidgetSettings)
router.get('/api/app-key')(getAppId)



#ACCESSIBILITY FOR LOG FILES
router.get('/api/all-log-files')(logfiles)
router.get('/api/single-log-file/{file_name}')(singleLogfile)



#DASHBORD
router.get('/dashboard')(dashboard_page)


app.include_router(router)
app.include_router(ws_router)
app.routes.extend(wsroutes)





