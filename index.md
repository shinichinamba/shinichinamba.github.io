---
layout: home
limit: 10
entries_layout: list
---

![MyPicture]({{ site.baseurl }}/assets/img/0141.jpg)

{% include profile-bio.html lang="en" %}

News
----
* **Sep 3, 2026**	Updated the publication list!
* **Oct 16, 2022**	Started my homepage!
{: .notice--accent}

<HR>

Research Interests
------------------
{{ site.data.profile.research_interests.en }}

<HR>

Job
---
{% assign jobs = site.data.cv.appointments | concat: site.data.cv.clinical_training | sort: "sort_seq" %}
{% include cv-section.html rows=jobs lang="en" fields="position,department,institution" %}

<HR>

Education
---------
{% include cv-section.html rows=site.data.cv.education lang="en" fields="degree,field,department,institution" nofallback="degree" %}

<HR>

Awards
------
{% include cv-section.html rows=site.data.cv.awards lang="en" fields="award,organization" %}

<HR>

Fellowships
-----------
{% include cv-section.html rows=site.data.cv.fellowships lang="en" fields="fellowship,organization" %}

<HR>

Grants (as Principal Investigator)
----------------------------------
{% assign grants_pi = site.data.cv.grants | where_exp: "g", "g.role == 'PI'" %}
{% include cv-grants.html rows=grants_pi lang="en" %}

<HR>

Teaching Experience
-------------------
{% include cv-section.html rows=site.data.cv.teaching lang="en" fields="course,school,institution" %}

<HR>

Selected Publications [[full list]]({{ site.baseurl }}/publications)
--------------------------------------------------------------------
\* denotes equal contribution; \*\* denotes (co-)corresponding authors

{% bibliography --query @*[status=selected] %}
