from django.utils.safestring import mark_safe
import copy

class PageNumberPagination(object):
    def __init__(self, request, queryset, page_size=10, plus=5, page_param='page'):
        """
        :param request: Request object
        :param queryset: Data that meets the conditions
        :param page_size: Number of data displayed on the page
        :param plus: Number of pages to display before and after
        :param page_param: Parameter to get pagination in the URL
        """
        query_dict = copy.deepcopy(request.GET)
        query_dict._mutable = True
        self.query_dict = query_dict
        self.page_param = page_param

        # Get page number
        page = request.GET.get(page_param, '1')
        if page.isdecimal():
            page = int(page)
        else:
            page = 1
        self.page = page
        self.page_size = page_size
        self.page_start = (page - 1) * self.page_size
        self.page_end = page * self.page_size

        # Get total count and slice
        total_count = queryset.count()  # Get total count before slicing
        self.queryset = queryset[self.page_start:self.page_end]

        # Calculate total pages
        total_page_count, div = divmod(total_count, self.page_size)
        if div:
            total_page_count += 1
        self.total_page_count = total_page_count
        self.plus = plus

    def html(self):
        # Calculate pagination range
        if self.total_page_count <= 2 * self.plus + 1:
            start_page = 1
            end_page = self.total_page_count
        else:
            if self.page <= self.plus:
                start_page = 1
                end_page = 2 * self.plus + 1
            else:
                if (self.page + self.plus - 1) > self.total_page_count:
                    start_page = self.total_page_count - 2 * self.plus
                    end_page = self.total_page_count
                else:
                    start_page = self.page - self.plus
                    end_page = self.page + self.plus

        # Generate pagination HTML using Bootstrap style
        page_str_list = []

        # First Page
        self.query_dict[self.page_param] = 1
        first_page = '<li class="page-item"><a class="page-link" href="?{}">First Page</a></li>'.format(self.query_dict.urlencode())
        page_str_list.append(first_page)

        # Previous page
        if self.page > 1:
            self.query_dict[self.page_param] = self.page - 1
            prev = '<li class="page-item"><a class="page-link" href="?{}">Previous Page</a></li>'.format(self.query_dict.urlencode())
        else:
            prev = '<li class="page-item disabled"><a class="page-link" href="#">Previous Page</a></li>'
        page_str_list.append(prev)

        # Current page numbers
        for i in range(start_page, end_page + 1):
            self.query_dict[self.page_param] = i
            if i == self.page:
                cur = '<li class="page-item active"><a class="page-link" href="?{}">{}</a></li>'.format(self.query_dict.urlencode(), i)
            else:
                cur = '<li class="page-item"><a class="page-link" href="?{}">{}</a></li>'.format(self.query_dict.urlencode(), i)
            page_str_list.append(cur)

        # Next page
        if self.page < self.total_page_count:
            self.query_dict[self.page_param] = self.page + 1
            nex = '<li class="page-item"><a class="page-link" href="?{}">Next Page</a></li>'.format(self.query_dict.urlencode())
        else:
            nex = '<li class="page-item disabled"><a class="page-link" href="#">Next Page</a></li>'
        page_str_list.append(nex)

        # Last Page
        self.query_dict[self.page_param] = self.total_page_count
        last_page = '<li class="page-item"><a class="page-link" href="?{}">Last Page</a></li>'.format(self.query_dict.urlencode())
        page_str_list.append(last_page)

        # Add jump to page form
        search_str = '''
        <form method="get" action="" class="d-inline">
            <input type="number" name="page" min="1" class="form-control d-inline w-auto" placeholder="Go to page">
            <button type="submit" class="btn btn-primary">Go</button>
        </form>
        '''
        page_str_list.append(search_str)

        # Join the list into a string and mark it as safe HTML
        page_str = mark_safe('<ul class="pagination">' + ''.join(page_str_list) + '</ul>')
        return page_str
