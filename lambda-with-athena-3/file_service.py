import tempfile
import json
import os


class FileService:
    def __init__(self):
        self.temp_file = None
        self.file_path = None

    def create_temp_file(self, suffix=".json"):
        """
        Create a temporary file for writing.
        """
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=suffix)
        self.file_path = self.temp_file.name
        self.temp_file.write("[")  # Start a JSON array

    def append_to_file(self, data: list):
        """
        Append a list of dictionaries (data) to the temporary file.

        Args:
            data (list): List of dictionaries to append.
        """
        if not self.temp_file:
            raise RuntimeError("Temporary file not initialized. Call create_temp_file() first.")

        for record in data:
            json.dump(record, self.temp_file)
            self.temp_file.write(",")  # Add a comma after each record

    def finalize_file(self):
        """
        Finalize the temporary file by removing the trailing comma and closing the JSON array.
        """
        if not self.temp_file:
            raise RuntimeError("Temporary file not initialized. Call create_temp_file() first.")

        # Move back to overwrite the last trailing comma and close the array
        self.temp_file.seek(self.temp_file.tell() - 1)
        self.temp_file.write("]")
        self.temp_file.close()

    def get_file_path(self):
        """
        Get the path of the temporary file.

        Returns:
            str: Path to the temporary file.
        """
        if not self.file_path:
            raise RuntimeError("File path not available. Ensure the file was created.")
        return self.file_path

    def delete_temp_file(self):
        """
        Delete the temporary file.
        """
        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)
            self.file_path = None
