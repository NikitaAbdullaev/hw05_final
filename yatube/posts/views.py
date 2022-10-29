from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Group, Follow, Post


User = get_user_model()

NUMBER_OF_POSTS_DISPLAYED: int = 10


def get_page_object(request, input_list, number_of_records):
    paginator = Paginator(input_list, number_of_records)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    template = 'posts/index.html'
    post_list = Post.objects.select_related('author').all()
    page_obj = get_page_object(request, post_list, NUMBER_OF_POSTS_DISPLAYED)
    context = {
        'title': 'Последние обновления на сайте',
        'page_obj': page_obj,
        'index': True,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = get_page_object(request, posts, NUMBER_OF_POSTS_DISPLAYED)
    context = {
        'title': f'Записи сообщества {slug}',
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    author_posts = author.posts.all()
    page_obj = get_page_object(
        request,
        author_posts,
        NUMBER_OF_POSTS_DISPLAYED
    )
    if request.user.is_authenticated:
        if Follow.objects.filter(user=request.user, author=author).exists():
            is_follower = True
        else:
            is_follower = False
    else:
        is_follower = False
    context = {
        'title': 'Профайл пользователя',
        'page_obj': page_obj,
        'author': author,
        'following': is_follower,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            form.save()
            return redirect('posts:profile', request.user.username)
        return render(request, 'posts/create_post.html', {'form': form})
    form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = get_page_object(request, posts, NUMBER_OF_POSTS_DISPLAYED)
    context = {
        'title': 'Посты избранных авторов',
        'follow': True,
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    follower = Follow()
    if request.user.username == username:
        return redirect('posts:profile', username)
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(user=request.user, author=author).exists():
        return redirect('posts:index')
    follower.user = request.user
    follower.author = author
    follower.save()
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    following = Follow.objects.filter(user=request.user, author=author)
    following.delete()
    return redirect('posts:profile', username)
