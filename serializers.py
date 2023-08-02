from settings import JWT_SETTINGS
from pydantic import BaseModel, Field
from fastapi import Query
from enum import Enum
from typing import List, Optional
from typing_extensions import TypedDict


class ErrMsgSerializer(BaseModel):
    message: str

# JWT
# JWT secret for encoding & decoding

class SettingsSerializer(BaseModel):
    authjwt_algorithm: str = JWT_SETTINGS["ALGORITHM"]
    authjwt_secret_key: str = JWT_SETTINGS["SECRET_KEY"]
    authjwt_access_token_expires = JWT_SETTINGS["ACCESS_TOKEN_EXPIRE_MINUTES"]
    authjwt_refresh_token_expires = JWT_SETTINGS["ACCESS_TOKEN_REFRESH_EXPIRE_MINUTES"]
    authjwt_token_location = JWT_SETTINGS["TOKEN_LOCATION"]


##########################################################################################################


# User creation Serializers
class UserInSerializer(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    password2: str




# User login token
class TokenCreateInSerializer(BaseModel):
    email: str
    password: str


class TokenRefreshInSerializer(BaseModel):
    access_token: str



# ------------------------  SETTINGS / PERSONAL / PROFILE  ------------------------------------------------


class ProfileDataSerializer(BaseModel):
    first_name: str
    last_name: str
    designation : str
    country_code : int
    contact_number : int
    
    
class ForgotPasswordSerializer(BaseModel):
    email : str 

class ResetPasswordSerializer(BaseModel):
    new_password: str
    confirm_password : str 
    
class ProfilePhotoSerializer(BaseModel):
    pic: str
    

class EmailUpdationSerializer(BaseModel):
    new_email: str
    
    
class PasswordUpdationSerializer(BaseModel):
    current_password: str
    new_password: str
    confirm_password : str
   
    
# ------------------------  Settings/ Personal/ Notification Preferences   --------------------------------------


class EmailNotificationSerializer(BaseModel):
    email_notification : str
    

class BrowserNotificationSerializer(BaseModel):
    notification_volume : int
    notification_sound : str
    
    
#--------------------------------- Settings / Company / General -----------------------------------------------------

class  CompanyDetailsSerializer(BaseModel):
    company_name : str
    company_url: str
    

class DomainUrlSeriializer(BaseModel):
    custom_domain_url : str
    

# ----------------------------------- Settings / Company / Teammates ---------------------------------------------------

class ChangeRoleSerializer(BaseModel):
    role : str
    user_id : int
    
class DeleteTeammateSerializer(BaseModel):
    user_id : int    
    
    
class TeammateInvitationSerializer(BaseModel):
    email: str
    role: str
    
class ResendInvitationSerializer(BaseModel):
    email: str
    
class DeleteInvitationSerializer(BaseModel):
    email: str
    
class RegisterInvitationSerializer(BaseModel):
    first_name: str
    last_name: str 
    password: str
    
    
class CreateTeamSerializer(BaseModel):
    team_name : str
    team_members : List[int]
    team_lead :int
    
class EditTeamSerializer(BaseModel):
    team_id : int
    team_name : str
    
class DeleteTeamSerializer(BaseModel):
    team_id : int
    
class AddTeammembersSerializer(BaseModel):
    team_id : int
    team_members : List[int]
    
class RemoveTeammateSerializer(BaseModel):
    team_id : int
    user_id : int
    
class AddBotToTeamSerializer(BaseModel):
    team_id : int
    bot_ids : List[int]   

class RemoveBotSerializer(BaseModel):
    team_id : int
    bot_id : int  

    
    
#----------------------------------- Settings / Company / CSAT RATINGS ----------------------------------------
class CsatRatingsSerializer(BaseModel):
    turn_on_csat : bool

  
  
  
#----------------------------------- Settings / Company / Fallback Emails ----------------------------------------
class FallbackEmailSerializer(BaseModel):
    turn_on_fallback_email : bool





# ------------------------------ Settings / Conversation/ Rules --------------------------------------

class AssignConversationSerializer(BaseModel):
    is_default_team:bool
    team_id:int
    
     
    
class SetRulesSerializer(TypedDict, total=True):
    is_default_team:bool
    team_id:int
    
    
class BotRoutingRulesSerializer(BaseModel):
    set_rules_for : SetRulesSerializer
    assign_conversation_to_bot : bool
    bot_selected : int = None


class HumanRoutingRulesSerializer(BaseModel):
    set_rules_for : SetRulesSerializer
    notify_everybody : bool
    selected_user : int = None
    
    
    
    
class ConvReassignmentSerializer(BaseModel):
    time_interval: int
    duration_type: str
    
    

class UnassignedBotReplySerializer(BaseModel):
    allow_unassigned_bots_to_reply : bool
    
    
    
# ------------------------------ Settings / Conversation/ Waiting Queue --------------------------------------

class WaitingQueueSerializer(BaseModel):
    enable_waiting_queue:bool
    
    
class MaxConcurrentChatsSerializer(BaseModel):
    max_concurrent_users:int
    


# ------------------------------ Settings / Conversation/ Auto Resolve --------------------------------------

class AutoResolveMessageSerilaizer(BaseModel):
    auto_resolve_message : str


class AutoResolveSerilaizer(BaseModel):
    auto_resolve_conversation : bool
    
    
    
    
# ------------------------------ Settings / Conversation/ Conversation Transcript-------------------------------------

class ConvTranscriptCompanySerilaizer(BaseModel):
    company_email : str
    
    
class ConvTranscriptUserSerilaizer(BaseModel):
    send_transcripts_to_user : bool
    
    
    
# ------------------------------ Settings / Conversation/ Quick Reply -------------------------------------

class AddQuickReplySerilaizer(BaseModel):
    shortcut_message : str
    full_message : str
    

class EditQuickReplySerilaizer(BaseModel):
    qr_id : int
    shortcut_message : str
    full_message : str
    

class DeleteQuickReplySerilaizer(BaseModel):
    qr_id : int
    
    
    
    
# ------------------------------ Settings / Conversation/ Pseudonym -------------------------------------

class PseudonymSerilaizer(BaseModel):
    show_pseudonyms : bool
    
    
    
    
# ------------------------------ Settings / ChatWidget/ Customization -------------------------------------

class WidgetStyleSerializer(BaseModel):
    color:str
    launcher_icon:str
    icon_image: str
    widget_position : str
    
    
    
class WidgetBrandingSerializer(BaseModel):
    show_branding:bool
   
   
   
class NotificationSoundSerializer(BaseModel):
    notification_sound:str
   
   
# ------------------------------ Settings / ChatWidget/ Configuration -------------------------------------

class SecureChatWidgetSerializer(BaseModel):
    remove_chat_history_on_page_refresh : bool
    history_removal_days : int
    history_removal_hours : int
    history_removal_minutes : int
    
    
class BotReplyDelaySerializer(BaseModel):
    delay_interval : int
    
class SingleThreadConvSerializer(BaseModel):
    is_enabled : bool
    
class DisableChatWidgetSerializer(BaseModel):
    disable_widget : bool
    
class DomainRestrictionSerializer(BaseModel):
    domain_list : List[str]
    
class TextToSpeechSerializer(BaseModel):
    is_enabled : bool
    
class SpeechToTextSerializer(BaseModel):
    is_enabled : bool
    
class HideAttachmentSerializer(BaseModel):
    is_enabled : bool
    



# ------------------------------ Settings / ChatWidget/ Greeting Message -------------------------------------

   
class GreetingMessageSerializer(BaseModel):
    enable_greeting_message : bool
    
    
    

class GreetingMessageOption(TypedDict, total=True):
    msg_option1 : str
    msg_option2 : str

    
class EditGreetingMessageSerializer(BaseModel):
    message_option : str
    options : GreetingMessageOption
    greeting_trigger_time: int
    play_notification_sound : bool 
    show_greeting_on_mobile : bool   
    
    
# ------------------------------ Settings / ChatWidget/ Pre chat lead collection -------------------------------------

class EnablePreChatLeadCollectionSerializer(BaseModel):
    enable_pre_chat_lead_collection : bool
    
    
class PreChatHeadingSerializer(BaseModel):
    pre_chat_heading : str
    
  
class AddPreChatFieldSerializer(BaseModel):
    is_mandatory : bool
    field_type : str 
    field_name : str 
    place_holder : str
    

  
class EditPreChatFieldSerializer(BaseModel):
    id : int
    is_mandatory : bool
    field_type : str 
    field_name : str 
    place_holder : str
    

  
class DeletePreChatFieldSerializer(BaseModel):
    id : int
    


# ------------------------------ Settings / ChatWidget/ Away message -------------------------------------
  
class AwayMessageSerializer(BaseModel):
    away_message_status : bool
    
    
 
class CollectEmailSerializer(BaseModel):
    collect_email_from_anonymous_users : bool
    
    
 
class KnownUsersAwayMessageSerializer(BaseModel):
    message : str
    
    
    
class UnknownUsersAwayMessageSerializer(BaseModel):
    message : str
    

# ------------------------------ Settings / ChatWidget/ Welcome message -------------------------------------

class WelcomeMessageSerializer(BaseModel):
    welcome_message_status : bool
    
#for email collection above serilizer is re-used

class AddWcMsgCategorySerializer(BaseModel):
    language_category : str
    

class DeleteWcMsgCategorySerializer(BaseModel):
    language_category : str
    
    
class AddWcMsgSerializer(BaseModel):
    message : List[str]
    language_category : str
 
 
class EditWcMsgSubSerializer(TypedDict, total=True):
    id : int
    message : str
    
class EditWcMsgSerializer(BaseModel):
    messages : List[EditWcMsgSubSerializer]
    
class AddWcMsgSubSerializer(TypedDict, total=True):
    messages : List[str]
    language_category : str
 
class DeleteWcMsgSerializer(BaseModel):
    id : int

class WcMsgCrudSerializer(BaseModel):
    addable_messages : AddWcMsgSubSerializer
    editable_messages : List[EditWcMsgSubSerializer] = []

#------------------------------------ Profile / Away  Mode -------------------------------------
class AwayModeSerializer(BaseModel):
    away_mode_status : bool
    
    
# ------------------------------------ Help-Center -------------------------------------------------

class AddHelpCenterCategorySerializer(BaseModel):
    category_title : str
    category_description : str
    
    
    
class EditHelpCenterCategorySerializer(BaseModel):
    category_id : int
    category_title : str
    category_description : str
    
    
    
class DeleteHelpCenterCategorySerializer(BaseModel):
    category_id : int
    
    
    
class ShowHelpCenterArticleSerializer(BaseModel):
    category_id : int
    article_id : int
    
    
class AddHelpCenterArticleSerializer(BaseModel):
    category_id : int
    status_and_visiblity : str
    article_title : str
    article_description : str
    
    



class ArticleCategorySerializer(TypedDict, total=True):
    current_category_id : int
    updated_category_id : int


class EditHelpCenterArticleSerializer(BaseModel):
    article_id : int
    article_title : str
    article_description : str
    status_and_visibility : str
    category_option : ArticleCategorySerializer
    
    
    
class DeleteHelpCenterArticleSerializer(BaseModel):
    category_id : int
    article_id : int    
    
    
    
class HelpCenterAppearance(TypedDict, total=True):
    primary_color : str
    headline_text : str
    searchbar_text : str
    logo_image : str
    fav_icon : str
    show_branding : bool
    show_live_chat_in_helpcenter : bool
     
     
class HelpCenterSettings(TypedDict, total=True):
    homepage_title : str
    google_tag_manager_id : str
    
    
class HelpCenterCustomizationSerializer(BaseModel):
    appearance : HelpCenterAppearance
    settings : HelpCenterSettings
    
    
class HelpCenterDomainUrlSerializer(BaseModel):
    custom_domain_url : str
    
    
    
#------------------------------------------ BOT INTEGRATIONS ----------------------------------------



class EditBotProfileSerializer(BaseModel):
    bot_id : int
    bot_name : str
    bot_photo : str
    


class EditBotHumanHandoffSerializer(BaseModel):
    bot_id : int
    allow_human_handoff : bool
    
    
    
#++++++++++++++++++++++  Dialogflow ES BOT integration ++++++++++++++++++++++++++
  
class DialogFlowESSerializer(BaseModel):
    private_key_file : str    # we will store the json as text in db
    default_bot_language : str
    dialogflow_region : str
    dialogflow_knowledge_base_id : List[str] = []

class DialogFlowESUpdateSerializer(BaseModel):
    bot_id : int
    private_key_file : str    # we will store the json as text in db
    default_bot_language : str
    dialogflow_region : str
    dialogflow_knowledge_base_id : List[str] = []
    
    
    
    
    
class DialogFlowCXSerializer(BaseModel):
    private_key_file : str    # we will store the json as text in db
    dialogflow_region : str
    agent_id : str

class DialogFlowCXUpdateSerializer(BaseModel):
    bot_id : int
    private_key_file : str    # we will store the json as text in db
    dialogflow_region : str
    agent_id : str
 
 
 
 
 
 
 
class CustomPlatformSerializer(BaseModel):
    webhook_url : str    # we will store the json as text in db
    header_key : str
    header_value : str
    platform_name : str


class CustomPlatformUpdateSerializer(BaseModel):
    bot_id : int
    webhook_url : str    # we will store the json as text in db
    header_key : str
    header_value : str
 
 
 
 
# ------------------------------------------ CUSTOMERS --------------------------------------------------
    
    
class AllCustomersSerializer(BaseModel):
    number_of_users :int
    page_number:int
    sort_column : str
    reverse : bool 

class DeleteCustomerSerializer(BaseModel):
    customer_id : str 
    
class BlockCustomerSerializer(BaseModel):
    customer_id : str 
    block : bool
    
    
    
#------------------------------------------------- CONVERSATION ----------------------------------------------------
class AddNewConversationSerializer(BaseModel):
    app_id : str


class AddCustomerEmailSerializer(BaseModel):
    customer_id : str 
    email : str


class AddCustomerRealnameSerializer(BaseModel):
    customer_id : str 
    name : str
    
    
class AddCustomerPhoneSerializer(BaseModel):
    customer_id : str 
    phone : int
    
    
class AddConversationTagSerializer(BaseModel):
    conversation_id : str 
    tag_name : str
    
    
class RemoveConversationTagSerializer(BaseModel):
    conversation_id : str 
    tag_name : str
    
    
class ConversationStatusSerializer(BaseModel):
    conversation_id : str
    conversation_status : str
    
    
class TagSerializer(BaseModel):
    tag_id : int
    
class EditTagSerializer(BaseModel):
    tag_id : int
    tag_name : str

class AddTagSerializer(BaseModel):
    tag_name : str



class ConvTeamSerializer(TypedDict, total=True):
    is_default : bool
    team_id : int

    
class ConversationAssignmmentSerializer(BaseModel):
    conversation_id : str
    assignee_type : str
    assignee_id : Optional[int] = None
    team =  ConvTeamSerializer  = {}
    
class TakeOverConversationSerilaizer(BaseModel):
    conversation_id : str
    
    
class SendTranscriptSerilaizer(BaseModel):
    customer_id : str
    conversation_id : str
    

class DateRangeSerilaizer(TypedDict, total=True):
    from_date : List[int]
    to_date : List[int]
    
class AssignConvFilterSerializer(TypedDict, total=True):
    assignee_type : str
    assignee_id : int
    
class ConversationFilterSerializer(BaseModel):
    date_range : DateRangeSerilaizer = {}
    status : List[str] = []
    tags : List[str] = []
    assigned_to : AssignConvFilterSerializer = {}
    
    
class CsatRatingSerilaizer(BaseModel):
    rating_type :int
    comment : str
    conversation_id :str
    
class OpPermissionTeammateSerializer(BaseModel):
    allow : bool
    
class OpPermissionBotSerializer(BaseModel):
    allow : bool
    
class OpPermissionTeamSerializer(BaseModel):
    allow : bool

# ==================================== AVAILABILITY =================================================
class ChangeAvailablitySerializer(BaseModel):
    is_available_status : bool
    
    
    
    
class ChangeConvOpenedSerializer(BaseModel):
    conversation_id: str
    status : bool