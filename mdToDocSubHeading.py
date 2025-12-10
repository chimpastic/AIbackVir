# --- 1. The Converter Logic (Core Logic) ---

class MarkdownToDocx:
    def __init__(self):
        self.document = Document()

    def convert(self, md_text):
        """
        Converts markdown text to a docx object.
        """
        # 1. Convert Markdown to HTML
        html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

        # 2. Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # 3. Iterate through top-level elements
        for element in soup.find_all(recursive=False):
            self._process_element(element)

        return self.document

    def _process_element(self, element):
        """Dispatches element processing based on tag name."""
        tag = element.name

        if tag.startswith('h') and len(tag) == 2:
            # Handle Headings
            try:
                level = int(tag[1])
                if 1 <= level <= 9:
                    self.document.add_heading(element.get_text(), level=level)
            except ValueError:
                pass # Ignore if not a valid integer

        elif tag == 'p':
            # Handle Paragraphs
            self.document.add_paragraph(element.get_text())

        elif tag in ['ul', 'ol']:
            # Handle Lists (Recursive)
            self._process_list(element, level=1)

        elif tag == 'table':
            # Handle Tables
            self._process_table(element)

    def _process_list(self, list_element, level=1):
        """
        Recursively processes lists to handle nesting.
        Maps HTML nesting to Word 'List Number 2', 'List Bullet 3', etc.
        """
        # Determine the style name based on tag type and nesting level
        is_ordered = list_element.name == 'ol'
        
        # Base style
        base_style = 'List Number' if is_ordered else 'List Bullet'
        
        # Word styles for levels > 1 are typically "List Number 2", "List Number 3"
        if level > 1:
            style_name = f"{base_style} {level}"
        else:
            style_name = base_style

        # Iterate through list items (li)
        for li in list_element.find_all('li', recursive=False):
            # 1. Extract the text for THIS item only (exclude nested lists text)
            text_parts = []
            nested_lists = []
            
            for child in li.contents:
                if child.name in ['ul', 'ol']:
                    nested_lists.append(child)
                else:
                    # Get text from strings or other inline tags like <b>, <code>
                    text_parts.append(child.get_text() if child.name else str(child))
            
            item_text = "".join(text_parts).strip()

            # 2. Add the paragraph with the calculated style
            if item_text:
                try:
                    self.document.add_paragraph(item_text, style=style_name)
                except KeyError:
                    # Fallback if the specific level style doesn't exist in the doc template
                    # (e.g., if "List Number 4" is missing, fall back to base)
                    print(f"Warning: Style '{style_name}' not found. Falling back to '{base_style}'.")
                    self.document.add_paragraph(item_text, style=base_style)

            # 3. Process nested lists (Recursion)
            for nested in nested_lists:
                self._process_list(nested, level=level + 1)

    def _process_table(self, table_element):
        """Parses an HTML table and adds it to the DOCX."""
        rows = table_element.find_all('tr')
        if not rows:
            return

        # Determine number of columns
        first_row_cols = rows[0].find_all(['th', 'td'])
        num_cols = len(first_row_cols)
        num_rows = len(rows)

        # Create table
        table = self.document.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Table Grid'

        for i, row in enumerate(rows):
            cols = row.find_all(['th', 'td'])
            for j, col in enumerate(cols):
                if j < num_cols:
                    cell = table.cell(i, j)
                    cell.text = col.get_text().strip()
                    if row.find('th'):
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.bold = True
