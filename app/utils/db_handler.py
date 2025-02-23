from sqlalchemy import create_engine
import pandas as pd
import logging
import json
from pathlib import Path
import os
from sqlalchemy import inspect

logger = logging.getLogger(__name__)

class DatabaseHandler:
    @staticmethod
    def generate_conn_string(memora_id: int) -> str:
        """Create a new database for a memora and return its connection string"""
        return f"sqlite:///memora_{memora_id}.db"

    @staticmethod
    def get_table_name_from_path(file_path: str, base_path: str) -> str:
        """
        Convert file path to table name using folder structure
        Example: /base/connections/contacts/synced_contacts.json -> connections__contacts__synced_contacts
        """
        # Get relative path from base_path
        rel_path = os.path.relpath(file_path, base_path)
        
        # Split path into components and remove file extension
        path_parts = Path(rel_path).with_suffix('').parts
        
        # Join parts with double underscore
        table_name = '__'.join(path_parts)
        
        # Clean table name (remove special characters, spaces)
        clean_table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
        
        # Ensure name starts with letter (SQLite requirement)
        if not clean_table_name[0].isalpha():
            clean_table_name = 'f_' + clean_table_name
            
        return clean_table_name

    @staticmethod
    def process_json_file(file_path: str, base_path: str) -> dict[str, pd.DataFrame]:
        """Process a JSON file and return a dict of DataFrames"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            table_name = DatabaseHandler.get_table_name_from_path(file_path, base_path)
            dfs = {}
            
            def flatten_json(data):
                """Convert nested structures to string representation"""
                if isinstance(data, (list, dict)):
                    return json.dumps(data)
                return data
            
            # If data is a list, convert directly to DataFrame
            if isinstance(data, list):
                if not data:  # Empty list
                    logger.warning("Empty list data in %s", file_path)
                    return {}
                df = pd.json_normalize(data)
                # Convert any remaining nested structures to strings
                for column in df.columns:
                    df[column] = df[column].apply(flatten_json)
                dfs[table_name] = df
            # If data is a dict, process each key separately
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        if not value:  # Empty list
                            logger.debug("Skipping empty list for key %s in %s", key, file_path)
                            continue
                        df = pd.json_normalize(value)
                        # Convert any remaining nested structures to strings
                        for column in df.columns:
                            df[column] = df[column].apply(flatten_json)
                        dfs[f"{table_name}__{key}"] = df
                    elif isinstance(value, dict):
                        if not value:  # Empty dict
                            logger.debug("Skipping empty dict for key %s in %s", key, file_path)
                            continue
                        df = pd.json_normalize([value])
                        # Convert any remaining nested structures to strings
                        for column in df.columns:
                            df[column] = df[column].apply(flatten_json)
                        dfs[f"{table_name}__{key}"] = df
            
            # Remove any empty DataFrames
            dfs = {k: v for k, v in dfs.items() if not v.empty and len(v.columns) > 0}
            
            if dfs:
                logger.info("Processed JSON file into tables: %s", list(dfs.keys()))
            else:
                logger.warning("No valid data found in JSON file: %s", file_path)
            
            return dfs
        except Exception as e:
            logger.error("Error processing JSON file %s: %s", file_path, str(e))
            return {}

    @staticmethod
    def process_html_file(file_path: str, base_path: str) -> dict[str, pd.DataFrame]:
        """Process an HTML file and return a dict of DataFrames"""
        try:
            # Read all tables from HTML file
            dfs = pd.read_html(file_path)
            
            # Create table name from path
            base_table_name = DatabaseHandler.get_table_name_from_path(file_path, base_path)
            
            # Create a dictionary with table names
            tables = {f"{base_table_name}__{i}": df for i, df in enumerate(dfs)}
            
            logger.info("Processed HTML file into tables: %s", list(tables.keys()))
            return tables
        except Exception as e:
            logger.error("Error processing HTML file %s: %s", file_path, str(e))
            return {}

    @staticmethod
    def save_dataframes(connection_string: str, dataframes: dict[str, pd.DataFrame]):
        """Save DataFrames to the database"""
        logger.info(f"Saving dataframes to {connection_string}")

        engine = create_engine(connection_string)

        for table_name, df in dataframes.items():
            try:
                # Skip empty DataFrames
                if df.empty:
                    logger.warning("Skipping empty DataFrame for table %s", table_name)
                    continue
                
                # Ensure we have at least one column
                if len(df.columns) == 0:
                    logger.warning("DataFrame for table %s has no columns, adding default column", table_name)
                    df['timestamp'] = pd.Timestamp.now()
                
                logger.info("Saving table %s with %d rows", table_name, len(df))
                df.to_sql(
                    table_name,
                    engine,
                    if_exists='replace',
                    index=False
                )
            except Exception as e:
                logger.error("Error saving DataFrame to database: %s", str(e))
            
        logger.info("Successfully saved %d tables to database", len(dataframes))
        

    @staticmethod
    def save_media_data(connection_string: str, media_type: str, data: list[dict]):
        """Save media data to specific tables in the database"""
        try:
            engine = create_engine(connection_string)
            
            # Group data by date (folder structure)
            grouped_data = {}
            for item in data:
                # Extract date from path (assuming folder structure like .../201807/...)
                path_parts = Path(item['path']).parts
                date = next((part for part in path_parts if part.isdigit() and len(part) == 6), None)
                
                # Get the last folder name for table name
                folder_name = "others"  # default
                for part in path_parts:
                    if part in ["stories", "posts", "profile", "reels"]:
                        folder_name = part
                        break
                
                if date:
                    if (folder_name, date) not in grouped_data:
                        grouped_data[(folder_name, date)] = []
                    
                    # Remove extract_memora_{id} from path
                    full_path = Path(item['path'])
                    relative_path = '/'.join(part for part in full_path.parts if not part.startswith('extract_memora_'))
                    
                    # Create row data based on media type
                    if media_type == "audio":
                        row_data = {
                            'date': date,
                            'filename': os.path.basename(item['path']),
                            'text': item.get('text', ''),
                            'uri': relative_path,
                            'metadata': json.dumps(item.get('metadata', {})),
                            'segments': json.dumps(item.get('segments', [])),
                            'language': item.get('language', ''),
                            'media_type': item.get('media_type', 'unknown')
                        }
                    else:
                        row_data = {
                            'date': date,
                            'filename': os.path.basename(item['path']),
                            'description': item.get('media_description', ''),
                            'uri': relative_path,
                            'text': item.get('text', ''),
                            'metadata': json.dumps(item.get('metadata', {})),
                            'media_type': item.get('media_type', 'unknown')
                        }
                    
                    grouped_data[(folder_name, date)].append(row_data)
            
            # Convert to DataFrame and save, grouped by folder name
            if grouped_data:
                # Group the data by folder name
                folder_groups = {}
                for (folder, date), rows in grouped_data.items():
                    if folder not in folder_groups:
                        folder_groups[folder] = []
                    folder_groups[folder].extend(rows)
                
                # Save each folder group to its own table
                for folder, rows in folder_groups.items():
                    df = pd.DataFrame(rows)
                    table_name = f"media__{folder}"
                    
                    df.to_sql(
                        table_name,
                        engine,
                        if_exists='append',
                        index=False
                    )
                    
                    logger.info("Saved %d records to table %s", len(df), table_name)
            else:
                logger.warning("No data found to save for media type: %s", media_type)
                
        except Exception as e:
            logger.error("Error saving media data to database: %s", str(e)) 

    @staticmethod
    def get_tables_that_contains(memora_id: int, text: str) -> list[str]:
        """Get all table names that end with the specified suffix"""
        try:
            connection_string = DatabaseHandler.generate_conn_string(memora_id)

            engine = create_engine(connection_string)
            inspector = inspect(engine)
            all_tables = inspector.get_table_names()
            matching_tables = [table for table in all_tables if text in table]
            
            logger.info(f"Found {len(matching_tables)} tables with text '{text}'")
            return matching_tables
        except Exception as e:
            logger.error(f"Error getting tables with text '{text}': {str(e)}")
            return [] 

    @staticmethod
    def read_table(memora_id: int, table_name: str) -> pd.DataFrame:
        """Read a table from the database and return it as a DataFrame"""
        try:
            connection_string = DatabaseHandler.generate_conn_string(memora_id)

            engine = create_engine(connection_string)
            df = pd.read_sql_table(table_name, engine)
            logger.info(f"Successfully read table '{table_name}' with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error reading table '{table_name}': {str(e)}")
            return pd.DataFrame() 