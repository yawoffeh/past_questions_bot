"""Functions file."""
import logging
import os
import re
import sys
import time
from typing import Dict, List, Union

import dotenv
import requests

# Polling Selenium setup
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Used when polling.
from webdriver_manager.chrome import ChromeDriverManager

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: %(message)s")

dotenv.load_dotenv()
# Constants
URL = os.getenv("URL")
USER_NAME = os.getenv("USER_NAME")
PASSWORD = os.getenv("PASSWORD")
# USER_NAME = os.environ.get("USER_NAME")
# PASSWORD = os.environ.get("PASSWORD")


class Functions:
    """Functions class."""

    def __init__(self, path):
        """Initializes a headless chrome browser and logs in to a website.

        Args:
          path: the path to the directory where the pdf's will be downloaded
        """
        self.path = path
        s = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        # Open externally not with chrome's pdf viewer
        self.PROFILE = {
            "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
            "download.default_directory": path,
            "download.extensions_to_open": "",
        }
        options.add_experimental_option("prefs", self.PROFILE)
        options.add_argument("--no-sandbox")
        options.headless = True
        self.driver = webdriver.Chrome(service=s, options=options)

        # Log in
        try:
            self.driver.get(URL)
            username_field = self.driver.find_element(By.NAME, "memberID")
            password_field = self.driver.find_element(By.NAME, "memberPassWord")
            login_button = self.driver.find_element(By.NAME, "logMeIn")
            username_field.send_keys(USER_NAME)  # The newline is interpreted as enter
            password_field.send_keys(PASSWORD)
            login_button.click()
            logging.info("Logged in successfully, waiting for user input...")
        except:
            logging.critical("Failed to log in.")
            sys.exit("Error logging in.")

    def get_past_question_path(self, path: str) -> Union[str, None]:
        """It takes a path as an argument, checks if there are any pdf files in the path, and if there are, it returns the most recent file in the path.

        Args:
          path (str): The path to the directory where the file is located.

        Returns:
          The path of the latest file in the directory.
        """
        logging.info("Checking path for latest file.")
        file_path = os.listdir(path)

        user_file_path = [
            os.path.join(path, basename)
            for basename in file_path
            if basename.endswith(".pdf")
        ]
        if len(user_file_path) == 0:
            return None
        return max(user_file_path, key=os.path.getctime)

    def search_for_past_question(self, cleaned_pasco_name: str) -> int:
        """It searches for a past question on the website, and returns 0 if it was successful, and 1 if it wasn't.

        Args:
          cleaned_pasco_name (str): The name of the file you're searching for.

        Returns:
          The return value is the status code of the function.
        """
        logging.info(
            f"Searching for {cleaned_pasco_name}: The current_url is {self.driver.current_url}"
        )
        try:
            search_field = self.driver.find_element(By.NAME, "keywords")
            search_button = self.driver.find_element(By.NAME, "search")
            # Double Quotes give accurate queries
            search_field.send_keys(f'"{cleaned_pasco_name}"')
            search_button.click()
            logging.info(
                f"After searching for {cleaned_pasco_name}: The current_url is {self.driver.current_url}"
            )
            return 0
        except:
            logging.error(f"Failed to search for {cleaned_pasco_name}", exc_info=True)
            return 1

    def get_list_of_past_question(self) -> List[str]:
        """
        It retrieves the names, year and semester of past questions displayed then adds them to a list.

        Returns:
          A list of strings.
        """
        filtered_past_question_list: List[str] = []
        logging.info(f"Retrieving list of past question from {self.driver.current_url}")

        try:
            past_question_page = requests.get(self.driver.current_url)
            past_question_content = BeautifulSoup(past_question_page.content, "lxml")
            past_question_list = past_question_content.find_all(
                "div", class_="item biblioRecord"
            )
            logging.info("Got list of past questions successfully.")
        except:
            logging.error("Failed to find past questions.", exc_info=True)
            return filtered_past_question_list
        else:
            if past_question_list:
                for past_question in past_question_list:
                    past_question_title = past_question.find("a", class_="titleField")
                    past_question_year = past_question.find(
                        "div", class_="customField isbnField"
                    )
                    past_question_semester = past_question.find(
                        "div", class_="customField collationField"
                    )
                    filtered_past_question_list.append(
                        past_question_title.get_text()
                        + "\n"
                        + past_question_year.get_text()
                        + "\n"
                        + past_question_semester.get_text()
                    )
            logging.info(
                "Appended key aspects of past questions to filtered list successfully."
            )
            return filtered_past_question_list

    def clean_past_question_list(self, list_of_values: List[str]) -> str:
        """It takes a list of strings, and returns a string with each item in the list on a new line, with a number in front of it.

        Args:
          list_of_values (List[str]): List[str]

        Returns:
          A string
        """
        updated_list = []
        for value in range(len(list_of_values)):
            updated_list.append(
                f"{value+1}. " + re.sub("\n", ", ", list_of_values[value])
            )
            updated_list.append("")

        modified_text = "\n".join(value for value in updated_list)

        return modified_text

    def get_links_of_past_question(self) -> Dict[int, str]:
        """
        A function to retrieve the links of all the past questions displayed.

        output: A dictionary containing the index and the past question link.
        """
        past_question_links: Dict[int, str] = {}
        logging.info(
            f"Retrieving links of past question from {self.driver.current_url}"
        )

        try:
            past_question_page = requests.get(self.driver.current_url)
            past_question_content = BeautifulSoup(past_question_page.content, "lxml")
            past_question_list = past_question_content.find_all(
                "a", class_="titleField"
            )
            logging.info("Retrieved past question links successfully.")
        except:
            logging.error("Failed to extract links of past questions.", exc_info=True)
            return past_question_links
        else:
            for past_question_index in range(1, len(past_question_list) + 1):
                past_question_links[past_question_index] = (
                    "https://balme.ug.edu.gh"
                    + past_question_list[past_question_index - 1]["href"]
                )
            logging.info("Extracted past question links successfully.")

            return past_question_links

    def get_past_question(
        self, past_question_links: Dict[int, str], choice: int
    ) -> List[str]:
        """It takes in a dictionary of past question links and a choice from the user, then it moves to the url of the users choice and downloads the past question.

        Args:
          past_question_links (Dict[int, Any]): This is a dictionary of the past questions links.
          choice (int): The choice of the user.

        Returns:
          past_question_file
        """
        for index, past_question_link in past_question_links.items():
            if int(choice) == index:
                self.driver.get(past_question_link)  # Move to the url of users choice.
                logging.info(f"Moved to {past_question_link} successfully.")
                self.download_past_question()
                break

        past_question_file = self.get_past_question_path(self.path)
        return past_question_file

    def download_past_question(self) -> None:
        """Clicks on a button that opens a frame, then clicks on a button in the frame to download a file."""
        logging.info(f"Downloading past question from {self.driver.current_url}")
        file = self.driver.find_element(By.CLASS_NAME, "openPopUp")
        self.driver.execute_script(
            "arguments[0].click();", file
        )  # screen displayed is a frame, so adapts to a frame.
        wait = WebDriverWait(self.driver, 10)
        wait.until(
            EC.frame_to_be_available_and_switch_to_it((By.CLASS_NAME, "cboxIframe"))
        )
        wait.until(EC.element_to_be_clickable((By.ID, "download"))).click()

        logging.info("Downloading file...")
        self.driver.back()
        time.sleep(2)


if __name__ == "__main__":
    function_class = Functions(str(os.getcwd()))
    name = input("Please enter the course name : ")
    function_class.search_for_past_question(name)
    questions = function_class.get_list_of_past_question()
    pasco_links = function_class.get_links_of_past_question()
    user_choice = int(input("The number of the past question you want to download: "))
    function_class.get_past_question(pasco_links, user_choice)
