from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    tags: Mapped[list["Tag"]] = relationship(
        secondary="word_tags", back_populates="words"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(64), default="semantic")

    words: Mapped[list["Word"]] = relationship(
        secondary="word_tags", back_populates="tags"
    )


class WordTag(Base):
    __tablename__ = "word_tags"
    __table_args__ = (UniqueConstraint("word_id", "tag_id", name="uq_word_tag"),)

    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
