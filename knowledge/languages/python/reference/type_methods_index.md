# Python Type Methods Index

Source status: imported_unverified. This is a compact reference index only and is not connected to runtime advice.

- `str` methods return new strings because strings are immutable.
- `list` methods often mutate in-place.
- `dict` and `set` methods may mutate state and require caution in examples.

| method | type | description_pl | mutation_behavior | review_status |
| --- | --- | --- | --- | --- |
| lower | str | Zwraca tekst malymi literami. | returns_new_value | imported_unverified |
| upper | str | Zwraca tekst wielkimi literami. | returns_new_value | imported_unverified |
| strip | str | Usuwa biale znaki lub wskazane znaki z brzegow. | returns_new_value | imported_unverified |
| split | str | Dzieli tekst na liste fragmentow. | returns_new_value | imported_unverified |
| join | str | Laczy elementy iterowalne separatorem. | returns_new_value | imported_unverified |
| replace | str | Zwraca tekst z podmienionymi fragmentami. | returns_new_value | imported_unverified |
| startswith | str | Sprawdza prefiks tekstu. | no_mutation | imported_unverified |
| endswith | str | Sprawdza sufiks tekstu. | no_mutation | imported_unverified |
| append | list | Dodaje element na koniec listy. | mutates_in_place | imported_unverified |
| extend | list | Dodaje wiele elementow do listy. | mutates_in_place | imported_unverified |
| insert | list | Wstawia element pod indeksem. | mutates_in_place | imported_unverified |
| remove | list | Usuwa pierwsze wystapienie wartosci. | mutates_in_place | imported_unverified |
| pop | list | Usuwa i zwraca element. | mutates_in_place | imported_unverified |
| sort | list | Sortuje liste w miejscu. | mutates_in_place | imported_unverified |
| reverse | list | Odwraca liste w miejscu. | mutates_in_place | imported_unverified |
| keys | dict | Zwraca widok kluczy slownika. | no_mutation | imported_unverified |
| values | dict | Zwraca widok wartosci slownika. | no_mutation | imported_unverified |
| items | dict | Zwraca widok par klucz-wartosc. | no_mutation | imported_unverified |
| get | dict | Pobiera wartosc z opcjonalna wartoscia domyslna. | no_mutation | imported_unverified |
| update | dict | Aktualizuje slownik innymi wartosciami. | mutates_in_place | imported_unverified |
| pop | dict | Usuwa i zwraca wartosc dla klucza. | mutates_in_place | imported_unverified |
| clear | dict | Usuwa wszystkie wpisy. | mutates_in_place | imported_unverified |
| add | set | Dodaje element do zbioru. | mutates_in_place | imported_unverified |
| remove | set | Usuwa element lub rzuca KeyError. | mutates_in_place | imported_unverified |
| discard | set | Usuwa element bez bledu, jesli go brak. | mutates_in_place | imported_unverified |
| union | set | Zwraca sume zbiorow. | returns_new_value | imported_unverified |
| intersection | set | Zwraca czesc wspolna zbiorow. | returns_new_value | imported_unverified |
| difference | set | Zwraca roznice zbiorow. | returns_new_value | imported_unverified |
