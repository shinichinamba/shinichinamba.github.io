#!/bin/env ruby
# encoding: utf-8

require 'jekyll/scholar'
require 'uri'

module Jekyll
  class Scholar
    module Utilities
      def reference_tag(entry, index = nil)
        return missing_reference unless entry

        entry = entry.convert(*bibtex_filters) unless bibtex_filters.empty?
        reference = render_bibliography entry, index

        # link title
        reference = reference.gsub(/(.*\.) (.*\.) <i>(.*)<\/i> (.*\.) (\bdoi:(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?![\"&\'<>])\S)+)\b)/) { |c| "#{$1} <a href=\"https://doi.org/#{$6}\" target=\"_blank\" rel=\"noopener\">#{$2}</a> <i class=\"journal\">#{$3}</i> #{$4} #{$5}"}

        # highlight authorship
        reference = reference.gsub(/\**Namba, S|難波 真一/u){|c| "<strong>#{$&}</strong>"}

        # Author list with an expandable middle.
        #
        # The full list is always in the DOM; the authors between the visible
        # head and the author's own name are wrapped in hidden spans. Clicking
        # the ellipsis reveals them and swaps "et al." for a collapse link, so
        # the behaviour needs no server round-trip and degrades to the full
        # list when JavaScript is off (the spans simply stay as authored).
        #
        # The split on ".," follows the CSL output convention: every author is
        # rendered "Family, I." so ".," separates them. The final pair is
        # joined by " & " instead, which is why an N-author list yields N-1
        # chunks and a 7-author list is left untouched.
        def et_al(text)
          author_list = text.split(".,")
          return text if author_list.length <= 6

          self_idx = author_list.find_index { |c| c.include?("<strong>") }

          if self_idx.nil? || self_idx <= 5
            head = author_list[0..5]
            rest = author_list[6..-1] || []
            visible = head.join(".,") + "."
            hidden = rest.empty? ? "" :
              "<span class=\"au-rest\" hidden>, " + rest.join(".,").sub(/\A\s+/, "") + "</span>"
            tail = ""
          else
            head = author_list[0..4]
            middle = author_list[5...self_idx]
            rest = author_list[(self_idx + 1)..-1] || []
            visible = head.join(".,") + "."
            hidden = "<span class=\"au-rest\" hidden>, " + middle.join(".,").sub(/\A\s+/, "") + ".</span>"
            # The ", ..., " gap only makes sense while collapsed; expanded,
            # a plain ", " takes its place.
            tail = "<span class=\"au-gap\">, ..., </span>" \
                   "<span class=\"au-rest\" hidden>, </span>" +
                   author_list[self_idx].sub(/\A\s+/, "") + "."
            unless rest.empty?
              tail += "<span class=\"au-rest\" hidden>, " + rest.join(".,").sub(/\A\s+/, "") + "</span>"
            end
          end

          more = "<a class=\"au-toggle au-more\" role=\"button\" tabindex=\"0\" " \
                 "aria-label=\"Show all authors\">[\u2026]</a>"
          less = "<a class=\"au-toggle au-less\" role=\"button\" tabindex=\"0\" hidden>" \
                 "[Show fewer authors]</a>"
          etal = "<span class=\"au-etal\"> <i>et al.</i></span>"

          "<span class=\"authors\">" + visible + hidden + tail + " " + more +
            etal + " " + less + "</span>"
        end
        reference = reference.gsub(/(.*\.) <a/) { |c| "#{et_al($1)} <a"}

        # remove doi if necessary
        reference = reference.gsub(/\bdoi:.*$/, "")

        # link urls
        reference = reference.gsub(/\[([^\]]*)\]\(((?:(?:https?|ftp):\/)?\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)\)/) { |c| "<a class=\"btn btn-primary btn-xs fui-link\" href=\"#{$2}\" target=\"_blank\" rel=\"noopener\"><span class=\"icon-text\">#{$1}</span></a>" }

        content_tag reference_tagname, reference,
          :id => [prefix, entry.key].compact.join('-')
      end
    end

    class BibliographyTag < Liquid::Tag
      include Scholar::Utilities

      def render_items(items)
        bibliography = items.compact.each_with_index.map { |entry, index|
          reference = bibliography_tag(entry, index + 1)

          if generate_details?
            reference << link_to(details_link_for(entry),
              config['details_link'], :class => config['details_link_class'])
          end

          content_tag config['bibliography_item_tag'], reference, config['bibliography_item_attributes']
        }.join("\n")

        bibliography_list_attributes = config['bibliography_list_attributes']
        if labels.include? "split"
          if labels.include? "start"
            @@split_counter = items.length
          else
            bibliography_list_attributes = bibliography_list_attributes.merge({"start": @@split_counter + 1})
            @@split_counter += items.length
          end
        end

        content_tag bibliography_list_tag, bibliography,
          { :class => config['bibliography_class'] }.merge(bibliography_list_attributes)

      end
    end
  end
end