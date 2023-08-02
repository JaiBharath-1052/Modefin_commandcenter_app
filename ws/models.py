from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String


# Define as metadata only for tracking migrations
Base = declarative_base()

# # Define the tables
