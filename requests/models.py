# requests/models.py
from django.db import models
from django.contrib.auth.models import User # <--- THIS IMPORT IS CRUCIAL
from django.utils import timezone
from django.db.models.signals import post_save # This was there
from django.dispatch import receiver # <--- ADD THIS LINE

class UpcyclingRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upcycling_requests') # <--- THIS FIELD IS CRUCIAL
    product_type = models.CharField(max_length=100)
    material_details = models.TextField()
    style_preference = models.CharField(max_length=200, blank=True, null=True)
    pickup_location = models.CharField(max_length=255)
    budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=50, default='Request Received')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_artisan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_upcycling_requests')
    item_image = models.ImageField(upload_to='request_images/', blank=True, null=True)
    
    def __str__(self):
        return f"Request for {self.product_type} by {self.user.username if self.user else 'Guest'}"

# --- NEW ARTISAN PROFILE MODEL ---
class ArtisanProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artisan_profile')
    bio = models.TextField(blank=True, null=True)
    skills = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated skills (e.g., 'Sewing, Woodworking, Painting')")
    portfolio_link = models.URLField(max_length=200, blank=True, null=True)
    is_active_artisan = models.BooleanField(default=False) # To activate/deactivate artisan accounts

    def __str__(self):
        return f"{self.user.username}'s Artisan Profile"

class Offer(models.Model):
    request = models.ForeignKey(UpcyclingRequest, on_delete=models.CASCADE, related_name='offers')
    artisan = models.ForeignKey(ArtisanProfile, on_delete=models.CASCADE, related_name='made_offers')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_completion_days = models.IntegerField(help_text="Estimated days to complete the upcycling project")
    message = models.TextField(blank=True, null=True, help_text="Message from the artisan to the requester")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Accepted', 'Accepted'),
            ('Rejected', 'Rejected'),
        ],
        default='Pending'
    )

    class Meta:
        # Ensures an artisan can only make one offer per request
        unique_together = ('request', 'artisan')
        ordering = ['price'] # Order offers by price by default (cheapest first)

    def __str__(self):
        return f"Offer by {self.artisan.user.username} for Request {self.request.id} - Status: {self.status}"
    
# --- SIGNAL TO CREATE ARTISAN PROFILE WHEN A NEW USER IS CREATED ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Check if this user is explicitly an artisan from registration, or default to not active
        # For now, we'll create a profile and leave is_active_artisan as False by default
        ArtisanProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'artisan_profile'): # Check if the profile already exists
        instance.artisan_profile.save()

# NEW: Conversation Model
class Conversation(models.Model):
    # Link to the UpcyclingRequest this conversation is about
    # This makes sense for a messaging system tied to specific requests.
    upcycling_request = models.ForeignKey(
        'UpcyclingRequest',
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True, blank=True # Allow conversation creation even if request link isn't immediately available
    )
    # Participants in the conversation. For a 1-to-1 chat, these are the two users.
    participant1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_p1'
    )
    participant2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_p2'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensures a unique conversation between two participants for a specific request.
        # This prevents duplicate chat threads for the same request.
        unique_together = ('upcycling_request', 'participant1', 'participant2')
        ordering = ['-updated_at'] # Order by most recently updated conversation

    def __str__(self):
        request_info = f" (Request: {self.upcycling_request.id})" if self.upcycling_request else ""
        return f"Conversation between {self.participant1.username} and {self.participant2.username}{request_info}"

# NEW: Message Model
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp'] # Order messages chronologically

    def __str__(self):
        return f"Message from {self.sender.username} in Conversation {self.conversation.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"