from tg.oms.models.text_page import TextTypeScene

class Image(TextTypeScene):
    
    __page_name__ = 'image'
    
    async def content_worker(self) -> str:
        self.content = await super().content_worker()
        
        self.content = self.content.replace('None', 'Не задано')
        return self.content