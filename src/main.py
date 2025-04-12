from core import XCoreClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    try:
        client = XCoreClient()
        logging.info("Service started successfully")
        
        # メイン処理をここに追加
        # client.create_list("Test List")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()