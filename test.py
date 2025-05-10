import os
import time
import logging
from typing import Dict, List, Any, Optional
from browser_use import BrowserUse

logger = logging.getLogger(__name__)

class SatelliteBrowserAgent:
    """Component for browser-based satellite data interactions"""
    
    def __init__(self):
        self.browser = BrowserUse()
        self.current_session = None
    
    async def search_copernicus_browser(self, 
                                       location: str, 
                                       time_period: str, 
                                       image_type: str = "Optical") -> List[Dict[str, Any]]:
        """
        Search for satellite images using browser automation on Copernicus website
        
        Args:
            location: Area of interest
            time_period: Time period for search
            image_type: Type of imagery
            
        Returns:
            List of found products
        """
        try:
            # Start a browser session
            self.current_session = await self.browser.start_session()
            
            # Navigate to Copernicus Open Access Hub
            await self.current_session.goto("https://scihub.copernicus.eu/dhus/#/home")
            logger.info("Navigated to Copernicus Open Access Hub")
            
            # Wait for page to load completely
            await self.current_session.wait_for_load_state("networkidle")
            
            # Check if login is needed and handle authentication
            if await self._need_login():
                await self._perform_login()
            
            # Navigate to search interface
            await self.current_session.click("text=Open search")
            await self.current_session.wait_for_selector("input[placeholder='Search area']")
            
            # Enter location in search box
            await self.current_session.fill("input[placeholder='Search area']", location)
            await self.current_session.press("input[placeholder='Search area']", "Enter")
            
            # Set time period
            await self._set_time_period(time_period)
            
            # Set image type filter (e.g., select Sentinel-2 for optical)
            if image_type.lower() == "optical":
                await self.current_session.click("text=Sentinel-2")
            elif image_type.lower() == "radar" or image_type.lower() == "sar":
                await self.current_session.click("text=Sentinel-1")
            
            # Submit search
            await self.current_session.click("button:has-text('Search')")
            await self.current_session.wait_for_selector(".search-results")
            
            # Extract search results
            return await self._extract_search_results()
            
        except Exception as e:
            logger.error(f"Error during browser search: {str(e)}")
            return []
        finally:
            # Close the session when done
            if self.current_session:
                await self.browser.end_session()
                self.current_session = None
    
    async def download_product_browser(self, 
                                     product_id: str, 
                                     download_dir: str = "./downloaded_images") -> Optional[str]:
        """
        Download a specific product using browser
        
        Args:
            product_id: ID of the product to download
            download_dir: Directory to save the downloaded file
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            os.makedirs(download_dir, exist_ok=True)
            
            # Start browser session if needed
            if not self.current_session:
                self.current_session = await self.browser.start_session()
                await self.current_session.goto("https://scihub.copernicus.eu/dhus/#/home")
                
                if await self._need_login():
                    await self._perform_login()
            
            # Navigate to product page
            await self.current_session.goto(f"https://scihub.copernicus.eu/dhus/#/details?id={product_id}")
            await self.current_session.wait_for_selector("button:has-text('Download')")
            
            # Configure download location
            await self.current_session.context.set_default_download_directory(download_dir)
            
            # Initiate download
            download_promise = self.current_session.wait_for_download()
            await self.current_session.click("button:has-text('Download')")
            download = await download_promise
            
            # Wait for download to complete
            downloaded_path = await download.path()
            logger.info(f"Downloaded file to {downloaded_path}")
            
            return downloaded_path
            
        except Exception as e:
            logger.error(f"Error downloading product {product_id}: {str(e)}")
            return None
    
    async def _need_login(self) -> bool:
        """Check if login is required"""
        login_button = await self.current_session.query_selector("text=Sign in")
        return login_button is not None
    
    async def _perform_login(self) -> None:
        """Perform login on Copernicus website"""
        username = os.environ.get('COPERNICUS_USERNAME')
        password = os.environ.get('COPERNICUS_PASSWORD')
        
        if not username or not password:
            logger.error("Login credentials not found in environment variables")
            raise ValueError("Copernicus credentials not configured")
        
        await self.current_session.click("text=Sign in")
        await self.current_session.wait_for_selector("input[name='username']")
        
        await self.current_session.fill("input[name='username']", username)
        await self.current_session.fill("input[name='password']", password)
        await self.current_session.click("button:has-text('Login')")
        
        # Wait for login to complete
        await self.current_session.wait_for_selector("text=Sign out", timeout=10000)
        logger.info("Successfully logged in to Copernicus")
    
    async def _set_time_period(self, time_period: str) -> None:
        """Set the time period for search"""
        # Click on the date filter
        await self.current_session.click(".date-filter")
        
        if "last" in time_period.lower():
            # Handle relative time periods
            if "day" in time_period.lower():
                days = int(time_period.lower().split("last")[1].strip().split()[0])
                await self.current_session.click("text=Last 24 hours")
            elif "week" in time_period.lower():
                await self.current_session.click("text=Last week")
            elif "month" in time_period.lower():
                await self.current_session.click("text=Last month")
            else:
                # Default to custom date range
                await self.current_session.click("text=Custom range")
                # Set appropriate dates based on the request
        elif "to" in time_period:
            # Handle explicit date ranges
            start_date, end_date = time_period.split("to")
            await self.current_session.click("text=Custom range")
            await self.current_session.fill(".start-date input", start_date.strip())
            await self.current_session.fill(".end-date input", end_date.strip())
        else:
            # Default to custom range with single date
            await self.current_session.click("text=Custom range")
            await self.current_session.fill(".start-date input", time_period.strip())
            await self.current_session.fill(".end-date input", time_period.strip())
    
    async def _extract_search_results(self) -> List[Dict[str, Any]]:
        """Extract search results from the page"""
        results = []
        
        # Get all result items
        result_elements = await self.current_session.query_selector_all(".search-result-item")
        
        for element in result_elements:
            try:
                # Extract product information
                title = await element.query_selector(".product-title")
                title_text = await title.text_content() if title else "Unknown"
                
                product_id = await element.get_attribute("data-product-id") or "Unknown"
                
                date_element = await element.query_selector(".acquisition-date")
                date = await date_element.text_content() if date_element else "Unknown"
                
                results.append({
                    "id": product_id,
                    "title": title_text,
                    "date": date,
                    "source": "Copernicus/Browser"
                })
            except Exception as e:
                logger.error(f"Error extracting result: {str(e)}")
        
        return results