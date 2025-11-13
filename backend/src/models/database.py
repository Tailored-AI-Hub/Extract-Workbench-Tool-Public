from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..db import Base
from .enums import ExtractionStatus

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    role = Column(String, nullable=False, default="user")  # 'admin' or 'user'
    name = Column(String, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

class PDFProject(Base):
    __tablename__ = "pdf_projects"

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None

class PDFFile(Base):
    __tablename__ = "pdf_files"
    
    uuid = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)                            # TODO: Why can't this be just a S3 Link?
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    page_count = Column(Integer, nullable=True)
    project_uuid = Column(String, ForeignKey("pdf_projects.uuid"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None
    
    @property
    def file_type(self):
        return "pdf"  # PDF files are always PDFs

class PDFFileExtractionJob(Base):
    __tablename__ = "pdf_file_extraction_jobs"
    
    uuid = Column(String, primary_key=True, index=True)
    pdf_file_uuid = Column(String, ForeignKey("pdf_files.uuid"), nullable=False, index=True)
    extractor = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ExtractionStatus.NOT_STARTED)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)  # latency in milliseconds
    cost = Column(Float, nullable=True)  # total cost
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp

class PDFFilePageContent(Base):
    __tablename__ = "pdf_file_page_content"
    
    uuid = Column(String, primary_key=True, index=True)
    pdf_file_uuid = Column(String, ForeignKey("pdf_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("pdf_file_extraction_jobs.uuid"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    metadata_ = Column(JSON, default=dict)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    __table_args__ = (
        {'extend_existing': True},
    )

class PDFFilePageFeedback(Base):
    __tablename__ = "pdf_file_page_feedback"
    
    uuid = Column(String, primary_key=True, index=True)
    pdf_file_uuid = Column(String, ForeignKey("pdf_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("pdf_file_extraction_jobs.uuid"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    feedback_type = Column(String, nullable=False, default="single")
    rating = Column(Integer, nullable=True)  # 1-5 rating
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None
    
    __table_args__ = (
        {'extend_existing': True},
    )

class PDFFileAnnotation(Base):
    __tablename__ = "pdf_file_annotations"

    uuid = Column(String, primary_key=True, index=True)
    pdf_file_uuid = Column(String, ForeignKey("pdf_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("pdf_file_extraction_jobs.uuid"), nullable=False, index=True)
    page_number = Column(Integer, index=True, nullable=False)
    text = Column(Text, nullable=False)
    comment = Column(Text, nullable=False)
    selection_start = Column(Integer, nullable=False)
    selection_end = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None


class AudioProject(Base):
    __tablename__ = "audio_projects"

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None


class AudioFile(Base):
    __tablename__ = "audio_files"

    uuid = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    duration_seconds = Column(Float, nullable=True)
    project_uuid = Column(String, ForeignKey("audio_projects.uuid"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None


class AudioFileExtractionJob(Base):
    __tablename__ = "audio_file_extraction_jobs"

    uuid = Column(String, primary_key=True, index=True)
    audio_file_uuid = Column(String, ForeignKey("audio_files.uuid"), nullable=False, index=True)
    extractor = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ExtractionStatus.NOT_STARTED)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class AudioFileContent(Base):
    __tablename__ = "audio_file_content"

    uuid = Column(String, primary_key=True, index=True)
    audio_file_uuid = Column(String, ForeignKey("audio_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("audio_file_extraction_jobs.uuid"), nullable=False, index=True)
    segment_number = Column(Integer, nullable=True, index=True)
    start_ms = Column(Integer, nullable=True)
    end_ms = Column(Integer, nullable=True)
    content = Column(JSON, nullable=False)
    metadata_ = Column(JSON, default=dict)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class AudioFileFeedback(Base):
    __tablename__ = "audio_file_feedback"

    uuid = Column(String, primary_key=True, index=True)
    audio_file_uuid = Column(String, ForeignKey("audio_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("audio_file_extraction_jobs.uuid"), nullable=False, index=True)
    segment_number = Column(Integer, nullable=True, index=True)
    feedback_type = Column(String, nullable=False, default="single")
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None


class AudioFileAnnotation(Base):
    __tablename__ = "audio_file_annotations"

    uuid = Column(String, primary_key=True, index=True)
    audio_file_uuid = Column(String, ForeignKey("audio_files.uuid"), index=True, nullable=False)
    extraction_job_uuid = Column(String, ForeignKey("audio_file_extraction_jobs.uuid"), index=True, nullable=False)
    segment_number = Column(Integer, nullable=True, index=True)
    selection_start_char = Column(Integer, nullable=True)
    selection_end_char = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None


class ImageProject(Base):
    __tablename__ = "image_projects"

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None


class ImageFile(Base):
    __tablename__ = "image_files"

    uuid = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    project_uuid = Column(String, ForeignKey("image_projects.uuid"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def owner_name(self):
        return self.owner.name if self.owner else None


class ImageFileExtractionJob(Base):
    __tablename__ = "image_file_extraction_jobs"

    uuid = Column(String, primary_key=True, index=True)
    image_file_uuid = Column(String, ForeignKey("image_files.uuid"), nullable=False, index=True)
    extractor = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ExtractionStatus.NOT_STARTED)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class ImageContent(Base):
    __tablename__ = "image_content"

    uuid = Column(String, primary_key=True, index=True)
    image_file_uuid = Column(String, ForeignKey("image_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("image_file_extraction_jobs.uuid"), nullable=False, index=True)
    content = Column(JSON, nullable=False)
    metadata_ = Column(JSON, default=dict)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class ImageFeedback(Base):
    __tablename__ = "image_feedback"

    uuid = Column(String, primary_key=True, index=True)
    image_file_uuid = Column(String, ForeignKey("image_files.uuid"), nullable=False, index=True)
    extraction_job_uuid = Column(String, ForeignKey("image_file_extraction_jobs.uuid"), nullable=False, index=True)
    feedback_type = Column(String, nullable=False, default="single")
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None


class ImageAnnotation(Base):
    __tablename__ = "image_annotations"

    uuid = Column(String, primary_key=True, index=True)
    image_file_uuid = Column(String, ForeignKey("image_files.uuid"), index=True, nullable=False)
    extraction_job_uuid = Column(String, ForeignKey("image_file_extraction_jobs.uuid"), index=True, nullable=False)
    selection_start_char = Column(Integer, nullable=True)
    selection_end_char = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Properties
    @property
    def user_name(self):
        return self.user.name if self.user else None