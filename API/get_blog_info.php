<?php
if (isset($_GET['url'])) {
    $url = $_GET['url'];

    // 使用 cURL 获取网页内容
    $curl = curl_init($url);
    curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($curl);
    curl_close($curl);

    // 使用 DOM 解析 HTML
    $doc = new DOMDocument();
    libxml_use_internal_errors(true);
    $doc->loadHTML($response);
    libxml_clear_errors();

    $title = "";
    $description = "";
    $rssUrl = "";

    // 获取标题
    $titleElements = $doc->getElementsByTagName("title");
    if ($titleElements->length > 0) {
        $title = $titleElements->item(0)->nodeValue;
    }

    // 获取描述
    $metaElements = $doc->getElementsByTagName("meta");
    foreach ($metaElements as $meta) {
        if ($meta->getAttribute("name") === "description") {
            $description = $meta->getAttribute("content");
            break;
        }
    }

    // 获取 RSS 地址
    $linkElements = $doc->getElementsByTagName("link");
    foreach ($linkElements as $link) {
        if ($link->getAttribute("type") === "application/rss+xml" || $link->getAttribute("type") === "application/atom+xml") {
            $rssUrl = $link->getAttribute("href");
            break;
        }
    }

    $result = [
        "title" => $title,
        "description" => $description,
        "rssUrl" => $rssUrl
    ];

    echo json_encode($result);
}
?>
