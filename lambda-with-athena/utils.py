
import pandas as pd
from aws_lambda_powertools import Logger

logger = Logger(service="AthenaUtils")

class AthenaUtils:
    @staticmethod
    def transform_results_to_dataframe(rows: list) -> pd.DataFrame:
        """
        Transform Athena query results into a Pandas DataFrame.

        Args:
            rows (list): ResultSet rows from Athena query.

        Returns:
            pd.DataFrame: DataFrame containing query results.
        """
        if not rows or len(rows) < 2:
            logger.info("No rows found or insufficient rows to create DataFrame.")
            return pd.DataFrame()

        # Extract headers from the first row
        headers = [col.get('VarCharValue', None) for col in rows[0]['Data']]
        logger.info(f"Extracted headers: {headers}")

        # Extract data rows
        data = [
            [col.get('VarCharValue', None) for col in row['Data']]
            for row in rows[1:]  # Skip the header row
        ]
        logger.info(f"Extracted data rows: {data[:5]} (showing up to 5 rows)")

        # Create DataFrame
        df = pd.DataFrame(data, columns=headers)
        logger.info(f"Created DataFrame with shape: {df.shape}")

        return df
