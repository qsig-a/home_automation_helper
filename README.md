# Home automation server

This is a FastAPI application designed for home automation tasks, with a primary focus on integrating with a [Vestaboard](https://www.vestaboard.com/) display.

Capabilities include:
- Posting custom messages to the Vestaboard.
- Displaying Boggle game grids.
- Showing random SFW/NSFW quotes from a database.

## Environment variables for the docker image

The following environment variables can be set to configure the application:

- `VESTABOARD_API_KEY`: Your Vestaboard API Key. Obtain this by creating an Installable API Key from the Vestaboard web interface.
- `VESTABOARD_API_SECRET`: Your Vestaboard API Secret. Obtain this alongside the API Key.
- `SAYING_DB_ENABLE`: Controls whether the saying database functionality is enabled. Set to "1" to enable, "0" to disable. (Default: `"0"`)
- `SAYING_DB_USER`: The username for connecting to the sayings database.
- `SAYING_DB_PASS`: The password for the database user.
- `SAYING_DB_HOST`: The hostname or IP address of the database server for sayings.
- `SAYING_DB_PORT`: The port number for the sayings database server. (Default: `3306`)
- `SAYING_DB_NAME`: The name of the database for sayings.

## API Endpoints

This section details the available API endpoints.

### `GET /`

-   **Description:** A basic health check endpoint.
-   **Request Body:** None.
-   **Response:**
    ```json
    {
        "message": "Hello, World! I am the home automation helper"
    }
    ```
-   **Example Usage:**
    ```bash
    curl http://localhost:8000/
    ```

### `POST /message`

-   **Description:** Posts a custom message directly to the Vestaboard.
-   **Request Body:** `MessageClass`
    ```json
    {
        "message": "Your message here"
    }
    ```
-   **Response:**
    ```json
    {
        "message": "Message sent successfully"
    }
    ```
    (Or an error detail if issues occur, e.g., invalid characters, Vestaboard API error)
-   **Example Usage:**
    ```bash
    curl -X POST http://localhost:8000/message -H "Content-Type: application/json" -d '{"message": "Hello from the API"}'
    ```

### `POST /games/boggle`

-   **Description:** Starts a Boggle game on the Vestaboard. The game grid (either 4x4 or 5x5) is displayed, and after a delay (200 seconds), the end grid/solution is shown.
-   **Request Body:** `BoggleClass`
    ```json
    {
        "size": 4
    }
    ```
    (Where `size` can be `4` or `5`)
-   **Response:**
    ```json
    {
        "message": "Boggle 4x4 game queued."
    }
    ```
    (Or an error detail if issues occur)
-   **Example Usage:**
    ```bash
    curl -X POST http://localhost:8000/games/boggle -H "Content-Type: application/json" -d '{"size": 4}'
    ```

### `GET /sfw_quote`

-   **Description:** Retrieves a random "Safe For Work" (SFW) quote from the database and displays it on the Vestaboard. Requires `SAYING_DB_ENABLE="1"`.
-   **Request Body:** None.
-   **Response:**
    ```json
    {
        "message": "Random SFW quote queued"
    }
    ```
    (Or an error detail if issues occur, e.g., database disabled/unavailable, no quote found, Vestaboard API error)
-   **Example Usage:**
    ```bash
    curl http://localhost:8000/sfw_quote
    ```

### `GET /nsfw_quote`

-   **Description:** Retrieves a random "Not Safe For Work" (NSFW) quote from the database and displays it on the Vestaboard. Requires `SAYING_DB_ENABLE="1"`.
-   **Request Body:** None.
-   **Response:**
    ```json
    {
        "message": "Random NSFW quote queued"
    }
    ```
    (Or an error detail if issues occur)
-   **Example Usage:**
    ```bash
    curl http://localhost:8000/nsfw_quote
    ```

## Setup and Running

This section explains how to set up and run the project using different methods.

### Local Development

Follow these steps to run the application on your local machine:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your_username/your_repository_name.git # Replace with the actual repository URL
    cd your_repository_name # Replace with the actual repository directory
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Ensure your virtual environment is activated, then run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a file named `.env` in the root directory of the project. This file will hold your environment-specific configurations.
    Refer to the "Environment variables for the docker image" section for a complete list of variables and their purpose.

    Here's an example structure for your `.env` file:
    ```env
    VESTABOARD_API_KEY="your_vestaboard_api_key"
    VESTABOARD_API_SECRET="your_vestaboard_api_secret"
    SAYING_DB_ENABLE="0" # Set to "1" to enable database features
    # SAYING_DB_USER="your_db_user"
    # SAYING_DB_PASS="your_db_password"
    # SAYING_DB_HOST="localhost"
    # SAYING_DB_PORT="3306"
    # SAYING_DB_NAME="sayings_db"
    ```

5.  **Run the application:**
    Once the dependencies are installed and your `.env` file is configured, you can start the FastAPI application using Uvicorn:
    ```bash
    uvicorn app.main:app --reload
    ```
    The application will typically be available at `http://127.0.0.1:8000`. The `--reload` flag enables auto-reloading when code changes are detected.

### Docker

You can also run the application using Docker.

1.  **Build the Docker image:**
    Navigate to the root directory of the project (where the `Dockerfile` is located) and run:
    ```bash
    docker build -t home-automation-server .
    ```

2.  **Run the Docker container:**
    You can pass environment variables directly in the `docker run` command or use an environment file.

    **Option A: Passing variables directly**
    ```bash
    docker run -d -p 8000:8000 \
      --env VESTABOARD_API_KEY="your_vestaboard_api_key" \
      --env VESTABOARD_API_SECRET="your_vestaboard_api_secret" \
      --env SAYING_DB_ENABLE="0" \
      # Add other --env flags as needed based on the "Environment variables" section
      --name home-automation-app \
      home-automation-server
    ```

    **Option B: Using an environment file**
    Create a `.env` file (as described in the "Local Development" setup) in your project root. Then run:
    ```bash
    docker run -d -p 8000:8000 \
      --env-file .env \
      --name home-automation-app \
      home-automation-server
    ```
    The application inside the container will be accessible on your host machine at `http://localhost:8000`.

### Running Tests

This project uses `pytest` for unit and integration testing. Test dependencies are included in `requirements.txt`.

1.  **Ensure dependencies are installed:**
    If you haven't already, install all necessary dependencies including `pytest`:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run all tests:**
    Navigate to the root directory of the project and run:
    ```bash
    pytest
    ```

3.  **Run tests with more options:**
    *   To run tests for a specific file:
        ```bash
        pytest tests/test_main.py
        ```
    *   To run tests with increased verbosity (shows individual test names):
        ```bash
        pytest -v
        ```

Tests are also automatically executed via GitHub Actions on every push and pull request to the `main` branch, ensuring code quality and integration.

## Games

This application includes a Boggle game feature that can be displayed on the Vestaboard.

### Boggle

-   **Overview:** The Boggle game displays a grid of letters on the Vestaboard. The goal, typically, is to find as many words as possible from the adjacent letters. This implementation shows a starting grid and then, after a set time, an ending grid (which could be a solution or simply clear the board, depending on the `app.games.boggle.generate_boggle_grids` logic - currently it generates two distinct grids).

-   **Initiating a Game:**
    -   To start a Boggle game, use the `POST /games/boggle` API endpoint.
    -   You need to specify the `size` of the Boggle grid in the request body. Supported sizes are `4` (for a 4x4 grid) or `5` (for a 5x5 grid).
        ```json
        {
            "size": 4
        }
        ```
    -   Refer to the "API Endpoints" section for more details on using this endpoint.

-   **Game Progression:**
    1.  **Start Grid:** Upon calling the endpoint, the initial Boggle grid (e.g., a random set of letters) is generated and immediately sent to the Vestaboard for display.
    2.  **Game Duration:** The game runs for a fixed duration of 200 seconds (approximately 3 minutes and 20 seconds).
    3.  **End Grid:** After the 200-second duration, a second grid (the "end grid" or "solution grid") is automatically sent to the Vestaboard.

-   **Vestaboard Display:**
    -   The Boggle grids are displayed as arrays of letters on the Vestaboard. Each letter occupies one character slot on the board.
    -   The specific dice and letter distribution are handled by the `app.games.boggle` module.

## Sayings

The application can display random "Safe For Work" (SFW) or "Not Safe For Work" (NSFW) quotes/sayings on the Vestaboard.

### Overview

This feature fetches a random entry from a pre-populated database table (either SFW or NSFW quotes) and sends it to be displayed on the Vestaboard.

### Triggering Quotes

-   **SFW Quote:** To display a random SFW quote, use the `GET /sfw_quote` API endpoint.
-   **NSFW Quote:** To display a random NSFW quote, use the `GET /nsfw_quote` API endpoint.

Refer to the "API Endpoints" section for more details on using these endpoints.

### Database Requirement

-   **Enablement:** This feature is active when the `SAYING_DB_ENABLE` environment variable is set to `"1"`. If it's `"0"` (the default), these endpoints will likely return an error or indicate that the feature is disabled.
-   **Database System:** A MySQL database is expected.
-   **Connection:** Configure the database connection using the following environment variables: `SAYING_DB_HOST`, `SAYING_DB_USER`, `SAYING_DB_PASS`, `SAYING_DB_PORT`, and `SAYING_DB_NAME`. Refer to the "Environment variables for the docker image" section for details on these variables.
-   **Schema:**
    The database must contain two specific tables:
    1.  `sfw_quotes`: This table stores the Safe For Work quotes.
    2.  `nsfw_quotes`: This table stores the Not Safe For Work quotes.

    Each of these tables must have the following column structure:
    -   `quote` (TEXT or VARCHAR): This column holds the actual text of the saying.
    -   `source` (VARCHAR, optional): This column can be used to store the source or author of the quote. It is not currently displayed but may be used in the future.

    Example table creation (MySQL syntax):
    ```sql
    CREATE TABLE sfw_quotes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        quote TEXT NOT NULL,
        source VARCHAR(255)
    );

    CREATE TABLE nsfw_quotes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        quote TEXT NOT NULL,
        source VARCHAR(255)
    );
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
