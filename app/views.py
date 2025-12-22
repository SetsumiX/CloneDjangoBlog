from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Q
from .forms import UserRegisterForm, UserLoginForm, PostForm, CommentForm, UserProfileForm, MessageForm
from .models import Post, Like, Comment, UserProfile, Favorite, Message, Category, Product, Order
import yookassa
from django.conf import settings

yookassa.Configuration.account_id = settings.YOOKASSA_SHOP_ID
yookassa.Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"Аккаунт {username} успешно создан")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, "app/register.html", {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Неправильное имя пользователя или пароль!")

    else:
        form = UserLoginForm()
    return render(request, 'app/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')

@login_required # Проверка на вход в аккунт, будет ли показывать информацию не залогиненым
def home(request):
    # Получаем все объекты Post из базы данных
    posts = Post.objects.all()

    # Передаем список posts в шаблон home.html через контекст
    context = {
        'posts': posts, # 'posts' - это имя переменной, которое будет доступно в шаблоне
    }
    return render(request, 'app/home.html', context)

@login_required
def post_detail(request, post_id):
    # Получаем конкретный пост по ID или возвращаем 404, если не найден
    post = get_object_or_404(Post, id=post_id)

    user_liked = False
    user = request.user
    if user.is_authenticated:
        user_liked = post.likes.filter(user=user).exists()

    user_favorited = post.favorited_by.filter(user=request.user).exists()

    all_comments = Comment.objects.filter(post=post).select_related("author").prefetch_related("comment_likes").order_by("create_at")
    comment_tree = build_comment_tree(all_comments)

    comment_form = CommentForm(post_id=post_id)
    # Можно передать дополнительные данные, например, комментарии
    return render(request, 'app/post_detail.html',
                  {'post': post,
                   'user_liked': user_liked,
                   'comment_form': comment_form,
                   'comment_tree': comment_tree,
                   'user_favorited': user_favorited,})

@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Пост опубликован")
            return redirect('home')
    else:
        form = PostForm()
        return render(request, "app/post_create.html", {"form": form})

@login_required
def del_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        messages.error(request,"У вас нет прав для удаления поста")
        return redirect('home')
    if request.method == "POST":
        post_title = post.title
        post.delete()
        messages.success(request, f"Пост - {post_title}, был удалён")
        return redirect('home')
    messages.warning(request, "Хорошая попытка, но для удаления воспользуйтесь кнопкой - удаление поста")
    return redirect('post_detail', post_id=post_id)

@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like_object, created = Like.objects.get_or_create(user=request.user, post=post)

    if created:
        action = "Liked"
    else:
        like_object.delete()
        action = "Unliked"
    messages.info(request,f"{action} пост {post.title}.")

    next_url = request.META.get("HTTP_REFERER", reverse("home"))
    return HttpResponseRedirect(next_url)

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        messages.error(request, "У вас недостаточно прав для его изменения")
        return redirect('home')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, f"Пост {post.title} успешно обнавлён")
            return redirect("post_detail", post_id=post.id)

    else:
        form = PostForm(instance=post)
    return render(request, 'app/post_edit.html',  {'form': form, 'post': post})

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST, post_id=post_id)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, f"Сообщение к посту {post.title} было успешно добавлено")
            return redirect('post_detail', post_id=post.id)

    return redirect('post_detail', post_id=post.id)

# Построение комментариев в виде дерева
def build_comment_tree(comments):
    comment_dict = {}
    root_comments = []

    for comment in comments:
        comment_dict[comment.id] = {'comment': comment, 'replies': []}

    for item in comment_dict.values():
        comment_obj = item['comment']
        if comment_obj.parent_id:
            parent_item = comment_dict.get(comment_obj.parent_id)
            if parent_item:
                parent_item['replies'].append(item)
        else:
            root_comments.append(item)
    return root_comments

@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile, created = UserProfile.objects.get_or_create(user=user)
    return render(request, 'app/profile_view.html', {'profile_user': user, 'profile': profile})

@login_required
def profile_edit(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Профиль успешно обновлён")
            return redirect('profile_view', username=request.user.username)

    else:
        form = UserProfileForm(instance=profile, user=request.user)

    return render(request, 'app/profile_edit.html', {"form": form})

@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user).select_related('author__profile').prefetch_related('likes', 'comments')
    return render(request, 'app/my_posts.html', {'posts': posts})

@login_required
def favorites(request):
    favorite_entries = Favorite.objects.filter(user=request.user).select_related('post__author__profile').prefetch_related('post__likes', 'post__comments')
    posts = [entry.post for entry in favorite_entries]

    context = {
        'posts': posts,
    }

    return render(request, 'app/favorites.html', {'posts': posts})

@login_required
def toggle_favorite(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user:
        messages.error(request, "Нельзя добавить в избранное свой пост")
        next_url = request.META.get("HTTP_REFERER", reverse("home"))
        return HttpResponseRedirect(next_url)
    favorite_obj, created = Favorite.objects.get_or_create(user=request.user, post=post)
    if created:
        action = "добвален в избранное"
    else:
        favorite_obj.delete()
        action = "удалён из избранного"

    messages.info(request, f'Пост {post.title} был {action}')
    next_url = request.META.get('HTTP_REFERER', reverse('home'))
    return HttpResponseRedirect(next_url)

@login_required
def messages_list(request, recipient_id=None):
    send_by_me = Message.objects.filter(sender=request.user).values_list("recipient_id", flat=True)
    send_to_me = Message.objects.filter(recipient=request.user).values_list("sender_id", flat=True)
    all_contact_ids = set(list(send_by_me) + list(send_to_me))
    contacts = User.objects.filter(id__in=all_contact_ids).select_related("profile").distinct()
    contacts_with_unread = []
    for contact in contacts:
        unread_count = Message.objects.filter(
            sender=contact,
            recipient=request.user,
            is_read=False,
        ).count()
        contacts_with_unread.append({
            'contact': contact,
            'unread_count': unread_count,
        })
    def get_last_message_time(contact):
        last_message = Message.objects.filter(
            (Q(sender=request.user) & Q(recipient=contact)) |
            (Q(sender=contact) & Q(recipient=request.user))
        ).order_by('-timestamp').first()
        return last_message.timestamp if last_message else None

    sorted_contacts_with_unread = sorted(contacts_with_unread, key=lambda x: get_last_message_time(x["contact"]), reverse=True)
    selected_conversation = None
    selected_recipient = None
    if recipient_id:
        selected_recipient = get_object_or_404(User, id=recipient_id)
        if selected_recipient.id in all_contact_ids:
            Message.objects.filter(recipient=request.user, sender=selected_recipient, is_read=False).update(is_read=True)
            selected_conversation = Message.objects.filter(
                (Q(sender=request.user) & Q(recipient=selected_recipient)) |
                (Q(sender=selected_recipient) & Q(recipient=request.user))
            ).select_related('sender__profile').order_by('timestamp')

    unread_count_total = Message.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        'contacts_with_unread': sorted_contacts_with_unread,
        'selected_conversation': selected_conversation,
        'selected_recipient': selected_recipient,
        'unread_count_total': unread_count_total,
    }

    return render(request, "app/messages_list.html", context)

@login_required
def send_message(request, recipient_id):
    recipient = get_object_or_404(User, id=recipient_id)
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.save()
            messages.success(request, f"Сообщение успешно отправленно, кому:{recipient.username}")
            return redirect('messages_list', recipient_id=recipient.id)
    else:
        form = MessageForm()

    if request.method == "GET":
        return redirect('messages_list', recipient_id=recipient.id)

    context = {
        'form': form,
        'recipient': recipient,
    }

    return render(request, 'app/send_message.html', context)

def shop_home(request):
    products = Product.objects.select_related('category').all()
    categories = Category.objects.all()

    context = {
        "products": products,
        "categories": categories,
    }

    return render(request, "app/shop/home.html", context)

def shop_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category).select_related("category")
    categories = Category.objects.all()

    context = {
        "products": products,
        "category": category,
        "categories": categories,
    }

    return render(request, 'app/shop/category.html', context)

def shop_product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    context = {
        "product": product,
    }

    return render(request, "app/shop/product_detail.html", context)

def shop_checkout(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        quantity = int(request.POST.get('quantity', 1))
        total_price = product.price * quantity
        order = Order.objects.create(
            user = request.user,
            product = product,
            quantity = quantity,
            total_price = total_price,
        )


        paymant = yookassa.Payment.create({
            "amount": {
                "value": str(total_price),
                "current": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.build_absolute_uri("/shop/success"),
            },
            "capture": True,
            "description": f"Покупка {product.name}",
            "metadata": {
                "order_id": order.id,
            },
        })

        order.yookassa_payment_id = paymant.id
        order.save()
        return redirect(paymant.confirmation.confirmation_uri)
    return redirect("shop_product_detail", product_id=product_id)

def shop_success(request):
    return render(request, "app/shop/success.html")