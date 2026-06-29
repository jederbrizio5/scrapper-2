from typing import Any, Dict
from datetime import datetime
from src.modules.meta_ads.client.exceptions import ParsingException
from src.modules.meta_ads.dto import Ad, Page, Advertiser, Media, SearchResponse


class MetaParser:
    """Transforma respuestas crudas de Meta Ads en DTOs tipados."""

    @staticmethod
    def parse_search_response(raw_data: Dict[str, Any]) -> SearchResponse:
        try:
            ads_data = raw_data.get("data", [])
            ads = [MetaParser.parse_ad(ad_dict) for ad_dict in ads_data]

            paging = raw_data.get("paging", {})
            cursors = paging.get("cursors", {})
            next_cursor = cursors.get("after")

            # Nota: Meta Graph API normalmente no da un total_results exacto,
            # pero podríamos setearlo si estuviera en la respuesta.
            total_results = None

            return SearchResponse(
                ads=ads, next_cursor=next_cursor, total_results=total_results
            )
        except Exception as e:
            raise ParsingException(f"Error parseando SearchResponse: {str(e)}")

    @staticmethod
    def parse_ad(ad_dict: Dict[str, Any]) -> Ad:
        try:
            ad_id = ad_dict.get("id", "")

            creation_time_str = ad_dict.get("ad_creation_time")
            creation_time = None
            if creation_time_str:
                creation_time = datetime.strptime(creation_time_str, "%Y-%m-%d")

            page = Page(
                id=ad_dict.get("page_id", ""), name=ad_dict.get("page_name", "")
            )

            advertiser = Advertiser(
                id=ad_dict.get("page_id", ""), name=ad_dict.get("page_name", "")
            )

            # Parse media basic
            media = []
            if "snapshot_media_url" in ad_dict:
                media.append(Media(type="image", url=ad_dict["snapshot_media_url"]))

            body = (
                ad_dict.get("ad_creative_bodies", [""])[0]
                if ad_dict.get("ad_creative_bodies")
                else None
            )

            return Ad(
                id=ad_id,
                creation_time=creation_time,
                status="active",
                body=body,
                page=page,
                advertiser=advertiser,
                media=media,
            )
        except Exception as e:
            raise ParsingException(f"Error parseando Ad: {str(e)}")
