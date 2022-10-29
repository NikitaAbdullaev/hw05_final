import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        cls.second_group = Group.objects.create(
            title='second_test_group',
            description='second_test_group_description',
            slug='second_test_slug'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=(
                b'\x47\x49\x46\x38\x39\x61\x02\x00'
                b'\x01\x00\x80\x00\x00\x00\x00\x00'
                b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                b'\x0A\x00\x3B'
            ),
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), 1)

        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text, 'Тестовый текст')
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image.name, f'posts/{form_data["image"].name}')

        username = self.user.username
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': username}
            )
        )

    def test_edit_post(self):
        """Валидная форма изменяет запись в Post."""
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group
        )
        form_data = {
            'text': 'Измененнный тестовый текст',
            'group': self.second_group.id,
        }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertNotEqual(post.text, Post.objects.get(pk=post.id).text)
        self.assertEqual(Group.objects.get(pk=self.group.id).posts.count(), 0)

    def test_guest_user_cannot_change_database(self):
        """
        Неавторизованный пользователь не может добавлять или
        изменять пост.
        """
        count_post = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
        }
        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Утверждаем, что после отправки неавторизованным пользователем
        # post-запроса, количество постов не изменилось
        self.assertEqual(Post.objects.count(), count_post)

        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group
        )
        form_data = {
            'text': 'Измененнный тестовый текст',
            'group': self.second_group.id,
        }
        self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        # Утверждаем, что после отправки неавторизованным пользователем
        # post-запроса, в посте не изменились ни текст, ни группа
        self.assertEqual(Post.objects.get(pk=post.id).text, post.text)
        self.assertEqual(Post.objects.get(pk=post.id).group, post.group)


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_guest_user_cannot_add_comment(self):
        """Неавторизованный пользователь не может добавлять комментарии."""
        form_data = {
            'text': 'тестовый текст комментария',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        # Утверждаем, что пост-запрос от неавторизованного пользователя не
        # добавит ни одной записи в модель Comment ...
        self.assertEqual(Comment.objects.count(), 0)
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        # ... а от авторизованного добавит.
        self.assertEqual(Comment.objects.count(), 1)
