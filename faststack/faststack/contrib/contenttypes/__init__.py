"""
FastStack Content Types Framework

Provides generic relations to any model, similar to Django's ContentTypes.

Example:
    from faststack.contrib.contenttypes import ContentType
    from faststack.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    # Create a comment that can belong to any model
    class Comment(Model):
        content_type = ForeignKey(ContentType)
        object_id = IntegerField()
        content_object = GenericForeignKey('content_type', 'object_id')
        text = TextField()

    # Add comments to any model
    post = await Post.get(id=1)
    await Comment.create(content_object=post, text="Great post!")

    # Get all comments for a post
    comments = await Comment.filter(
        content_type=await ContentType.get_for_model(Post),
        object_id=post.id
    )
"""

from .models import ContentType, ContentTypeManager
from .fields import GenericForeignKey, GenericRelation
from .utils import get_content_type, get_object_for_content_type

__all__ = [
    'ContentType',
    'ContentTypeManager',
    'GenericForeignKey',
    'GenericRelation',
    'get_content_type',
    'get_object_for_content_type',
]
