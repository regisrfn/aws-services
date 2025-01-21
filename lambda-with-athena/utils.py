class AthenaUtils:
    @staticmethod
    def transform_results_to_dict(rows: list) -> list:
        """
        Transform Athena query results into a list of dictionaries.

        Args:
            rows (list): ResultSet rows from Athena query.

        Returns:
            list: List of dictionaries where keys are column names and values are row data.
        """
        if not rows or len(rows) < 2:
            return []

        # Extract headers from the first row
        headers = [col.get('VarCharValue', None) for col in rows[0]['Data']]

        # Transform remaining rows into dictionaries
        results = []
        for row in rows[1:]:  # Skip header row
            record = {headers[i]: col.get('VarCharValue', None) for i, col in enumerate(row['Data'])}
            results.append(record)

        return results
