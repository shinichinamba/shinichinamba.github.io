---
layout: home
limit: 10
entries_layout: list
---

難波 真一（なんば しんいち）
---------------------------

![MyPicture]({{ site.baseurl }}/assets/img/0141.jpg)

{% include profile-bio.html lang="ja" %}

更新情報
--------

* **2026/9/3**	論文リストを更新しました
* **2022/10/16**	ホームページを開設しました
{: .notice--accent}

<HR>

研究分野
--------

{{ site.data.profile.research_interests.ja }}

<HR>

職歴・学歴
----------

{% comment %}
  The Japanese page has always listed only the substantive appointments, so
  invited faculty positions are filtered out here. They remain in the data and
  still appear on the English page and on both CVs; delete the where_exp to
  show them here too.
{% endcomment %}
{% assign appts = site.data.cv.appointments | where_exp: "a", "a.appointment_type != 'invited'" %}
{% assign career = appts | concat: site.data.cv.clinical_training | concat: site.data.cv.education | sort: "sort_seq" %}
{% include cv-section.html rows=career lang="ja" fields="institution,department,field,position,degree" sep="　" nofallback="degree" %}

<HR>

受賞歴
------

{% include cv-section.html rows=site.data.cv.awards lang="ja" fields="organization,award" sep="　" %}

<HR>

奨学金
------

{% include cv-section.html rows=site.data.cv.fellowships lang="ja" fields="organization,fellowship" sep="　" %}

<HR>

競争的資金等の研究課題（代表）
-----------------------------

{% assign grants_pi = site.data.cv.grants | where_exp: "g", "g.role == 'PI'" %}
{% include cv-grants.html rows=grants_pi lang="ja" %}

<HR>

教育歴
------

{% include cv-section.html rows=site.data.cv.teaching lang="ja" fields="course,institution,school" sep="　" %}

<HR>

主要学術論文 [[一覧]]({{ site.baseurl }}/publications)
------------------------------------------------------

\* denotes equal contribution; \*\* denotes (co-)corresponding authors

{% bibliography --query @*[status=selected] %}
