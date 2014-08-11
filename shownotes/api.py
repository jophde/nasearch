import searches
import json
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage
from shownotes.models import Note, UrlEntry, TextEntry, Topic


def json_result(result):
    return {'show_number': result.show_number,
            'topic_name': result.topic_name,
            'title': result.text,
            'urls': [url for url in result.url_entries],
            'text': result.text_entry,
            'id': result.note_id}


def wrap_json(request, payload):
    """
    return HttpResponse with data correctly formatted for json or jsonp
    depending on the request
    """
    if 'callback' in request.GET:
        return HttpResponse('{}({})'.format(
            request.GET['callback'],
            json.dumps(payload)), content_type='text/javascript')
    else:
        return HttpResponse(json.dumps(payload),
                            content_type='application/json')


def paginate(results, page, limit):
    paginator = Paginator(results, limit)
    try:
        paged_results = paginator.page(page)
        return (paged_results, page, paginator.num_pages)
    except EmptyPage:
        return ([], 1, 1)


def topics(request):
    """
    return a list of paired topic names and ids
    """
    return wrap_json(
        request,
        [{'text': t.name, 'id': t.id} for t in Topic.objects.all()])


def search(request):
    """
    perform a search and return the matches
    recognised parameters are: topics, results_limit, page, string
    """
    RESULTS_LIMIT = 50
    TOPIC_LIMIT = 10
    topics = []
    if 'topics' in request.GET:
        topics = [int(t) for t in request.GET['topics'].split() if t.isdigit()]
    topics = topics[:TOPIC_LIMIT]
    string = ''
    if 'string' in request.GET:
        string = request.GET['string']
    limit = RESULTS_LIMIT
    if 'limit' in request.GET and request.GET['limit'].isdigit():
        limit = min(RESULTS_LIMIT, int(request.GET['limit']))
    page = 1
    if 'page' in request.GET and request.GET['page'].isdigit():
        page = int(request.GET['page'])

    response = {'results': [], 'page': 1, 'page_count': 1,
                'result_count': 0, 'page_result_count': 0}
    if string == '' and topics == []:
        return wrap_json(request, response)

    results = searches.search(string, topics)
    response['result_count'] = results.count()
    paged_results, response['page'], response['page_count'] = \
        paginate(results, page, limit)
    response['results'] = [json_result(x) for x in paged_results]
    response['page_result_count'] = len(paged_results)
    return wrap_json(request, response)


def show(request):
    """
    fetch all shownotes belonging to a specific show number
    """
    payload = []
    if 'number' in request.GET and request.GET['number'].isdigit():
        payload = [json_result(r) for r in
                   searches.topics_in_show(int(request.GET['number']))]
    return wrap_json(request, payload)


def note(request):
    """
    retrieve details of a specific note by id
    """
    if 'id' in request.GET and request.GET['id'].isdigit():
        try:
            note = Note.objects.get(id=int(request.GET['id']))
            urls = UrlEntry.get_by_note(note)
            text_entry = TextEntry.get_by_note(note)[0]
            payload = {'show_number': note.show.id,
                       'topic_name': note.topic.name,
                       'title': note.title,
                       'urls': [url.url for url in urls],
                       'text': text_entry.text,
                       'id': note.id}
        except Exception as e:
            print e
            payload = {}
    return wrap_json(request, payload)
